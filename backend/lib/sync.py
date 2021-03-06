import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from .. import app, db
from .models import Category, Keyword, Maintainer, Package, PackageVersion, PkgCheck

SYNC_BUFFER_SECS = 60*60 #1 hour
proj_url = "https://api.gentoo.org/metastructure/projects.xml"
pkg_url_base = "https://packages.gentoo.org/"
http_session = requests.session()


def get_project_data():
    projects = {}
    data = http_session.get(proj_url)
    if not data:
        print("Failed retrieving projects.xml")
        return projects
    root = ET.fromstring(data.content)
    # Parsing is based on http://www.gentoo.org/dtd/projects.dtd as of 2016-11-10
    if root.tag.lower() != 'projects':
        print("Downloaded projects.xml root tag isn't 'projects'")
        return projects
    for proj_elem in root:
        if proj_elem.tag.lower() != 'project':
            print("Skipping unknown <projects> subtag <%s>" % proj_elem.tag)
            continue
        proj = {
            'members': [],
            'subprojects': [],
        }
        for elem in proj_elem:
            tag = elem.tag.lower()
            if tag in ['email']:
                proj[tag] = elem.text.lower()
            elif tag in ['name', 'url', 'description']:
                proj[tag] = elem.text
            elif tag == 'member':
                member = {}
                if 'is-lead' in elem.attrib and elem.attrib['is-lead'] == '1':
                    member['is_lead'] = True
                for member_elem in elem:
                    member_tag = member_elem.tag.lower()
                    if member_tag in ['email']:
                        member[member_tag] = member_elem.text.lower()
                    elif member_tag in ['name', 'role']:
                        member[member_tag] = member_elem.text
                if 'email' in member:
                    proj['members'].append(member)
            elif tag == 'subproject':
                if 'ref' in elem.attrib:
                    # subprojects will be a list of (subproject_email, inherit-members) tuples where inherit-members is True or False.
                    # TODO: Might change if sync code will want it differently
                    proj['subprojects'].append((elem.attrib['ref'].lower(), True if ('inherit-members' in elem.attrib and elem.attrib['inherit-members'] == '1') else False))
                else:
                    print("Invalid <subproject> tag inside project %s - required 'ref' attribute missing" % proj['email'] if 'email' in proj else "<unknown>")
            else:
                print("Skipping unknown <project> subtag <%s>" % tag)
        if 'email' in proj:
            projects[proj['email']] = proj
        else:
            print("Skipping incomplete project data due to lack of required email identifier: %s" % (proj,))
    return projects

def sync_projects():
    projects = get_project_data()
    existing_maintainers = {}
    # TODO: Use UPSERT instead (on_conflict_do_update) if we can rely on postgresql:9.5
    for maintainer in Maintainer.query.all():
        existing_maintainers[maintainer.email] = maintainer
    for email, data in projects.items():
        if email in existing_maintainers:
            print ("Updating project %s" % email)
            existing_maintainers[email].is_project = True
            if 'description' in data:
                existing_maintainers[email].description = data['description']
            if 'name' in data:
                existing_maintainers[email].name = data['name']
            if 'url' in data:
                existing_maintainers[email].url = data['url']
        else:
            print ("Adding project %s" % email)
            new_maintainer = Maintainer(email=email, is_project=True, description=data['description'], name=data['name'], url=data['url'])
            db.session.add(new_maintainer)
            existing_maintainers[email] = new_maintainer

        members = []

        for subproject_email, inherit_members in data['subprojects']:
            # TODO: How should we handle inherit_members?
            if subproject_email in existing_maintainers:
                members.append(existing_maintainers[subproject_email])
            else:
                print("Creating new project entry for subproject: %s" % subproject_email)
                new_subproject = Maintainer(email=subproject_email, is_project=True)
                db.session.add(new_subproject)
                existing_maintainers[subproject_email] = new_subproject
                members.append(new_subproject)

        for member in data['members']:
            if member['email'] in existing_maintainers:
                # TODO: Stop overwriting the name from master data, if/once we have a proper sync source for individual maintainers (Gentoo LDAP?)
                if 'name' in member:
                    existing_maintainers[member['email']].name = member['name']
                members.append(existing_maintainers[member['email']])
            else:
                print("Adding individual maintainer %s" % member['email'])
                new_maintainer = Maintainer(email=member['email'], is_project=False, name=member['name'] if 'name' in member else None)
                db.session.add(new_maintainer)
                existing_maintainers[member['email']] = new_maintainer
                members.append(new_maintainer)

        # TODO: Include role information in the association?
        existing_maintainers[email].members = members
    db.session.commit()

def sync_categories():
    url = pkg_url_base + "categories.json"
    data = http_session.get(url)
    # TODO: Handle response error (if not data)
    categories = data.json()
    # TODO: Use UPSERT instead (on_conflict_do_update) if we can rely on postgresql:9.5
    existing_categories = {cat.name: cat for cat in Category.query.all()}
    for category in categories:
        if category['name'] in existing_categories:
            existing_categories[category['name']].description = category['description']
        else:
            new_cat = Category(name=category['name'], description=category['description'])
            db.session.add(new_cat)
    db.session.commit()

def sync_packages():
    for category in Category.query.all():
        data = http_session.get(pkg_url_base + "categories/" + category.name + ".json")
        if not data:
            print("No JSON data for category %s" % category.name) # FIXME: Better handling; mark category as inactive/gone?
            continue
        packages = data.json()['packages']
        # TODO: Use UPSERT instead (on_conflict_do_update)

        existing_packages = {pkg.name: pkg for pkg in category.packages}

        for package in packages:
            if package['name'] in existing_packages:
                continue # TODO: Update description once we keep that in DB
            else:
                new_pkg = Package(category=category, name=package['name'])
                db.session.add(new_pkg)
    db.session.commit()

def sync_pkgcheck():
    data = http_session.get("https://gitweb.gentoo.org/report/gentoo-ci.git/plain/output.xml")
    root = ET.fromstring(data.content)

    if root.tag.lower() != 'checks':
        print("Downloaded gentoo-ci output.xml root tag isn't 'checks'")
        return

    PkgCheck.query.delete()

    for result_elem in root:
        if result_elem.tag.lower() != 'result':
            print("Skipping unknown <checks> subtag <%s>" % result_elem.tag)
            continue

        check = {
            'category': None,
            'package': None,
            'version': None,
            'class': '',
            'message': '',
        }

        for elem in result_elem:
            tag = elem.tag.lower()
            text = elem.text

            if tag == 'category':
                category = Category.query.filter_by(name=text).first()
                if category:
                    check['category'] = category
                else:
                    print("Skipping unknown category <%s>" % text)
            elif tag == 'package':
                if check['category']:
                    package = Package.query.filter_by(category=check['category'],name=text).first()
                    if package:
                        check['package'] = package
                    else:
                        print("Skipping unknown package <%s>" % text)
                else:
                    print("Skipping package <%s> for which no category is defined" % text)
            elif tag == 'version':
                if check['package']:
                    version = PackageVersion.query.filter_by(package=check['package'], version=text).first()
                    if version:
                        check['version'] = version
                    else:
                        print("Skipping unknown version <%s-%s>" % (check['package'].name, text))
                else:
                    print("Skipping version <%s> for which no package is defined" % text)
            elif tag == 'class':
                check['class'] = elem.text.lower()
            elif tag == 'msg':
                check['message'] = elem.text.lower()

        pkgcheck = PkgCheck(category=check['category'], package=check['package'], version=check['version'], violationclass=check['class'], message=check['message'])
        db.session.add(pkgcheck)

    db.session.commit()

def sync_versions():
    """Synchronize packages version data from packages.gentoo.org.

    For each package that has not been updated in the last SYNC_BUFFER_SECS,
    pull package information and refresh its description, maintainers,
    versions and keywords.
    """
    cnt = 0
    ts = datetime.utcfromtimestamp(time.time() - SYNC_BUFFER_SECS)
    now = datetime.utcnow()
    existing_maintainers = {}
    for maintainer in Maintainer.query.all():
        existing_maintainers[maintainer.email] = maintainer

    all_keywords = {kwd.name: kwd for kwd in Keyword.query.all()}

    packages_to_sync = Package.query.filter(Package.last_sync_ts < ts).order_by(Package.last_sync_ts).all()
    print("Going to sync %d packages%s" % (len(packages_to_sync), (" (oldest sync UTC timestamp: %s)" % packages_to_sync[0].last_sync_ts if len(packages_to_sync) else "")))

    for package in packages_to_sync:
        cnt += 1
        data = http_session.get(pkg_url_base + "packages/" + package.full_name + ".json")
        if not data:
            print("No JSON data for package %s" % package.full_name) # FIXME: Handle better; e.g mark the package as removed if no pkgmove update
            continue

        pkg = data.json()

        print ("Updating package: %s" % package.full_name)

        # 1. refresh description
        if 'description' in pkg:
            package.description = pkg['description']

        # 2. refresh maintainers
        maintainers = []
        for maint in pkg.get('maintainers', []):
            if 'email' not in maint or 'type' not in maint:
                raise ValueError(
                    "Package %s maintainer %s entry not GLEP 67 valid" %
                    (package.full_name, maint)
                )

            email = maint['email'].lower()
            if email in existing_maintainers:
                maintainers.append(existing_maintainers[email])
            else:
                is_project = False
                if maint['type'] == 'project':
                    is_project = True
                print("Adding %s maintainer %s" % ("project" if is_project else "individual", email))
                new_maintainer = Maintainer(email=email, is_project=is_project, name=maint.get('name'))
                db.session.add(new_maintainer)
                existing_maintainers[email] = new_maintainer
                maintainers.append(new_maintainer)

        # Intentionally outside if 'maintainers' in pkg, because if there are no maintainers in JSON, it's falled to maintainer-needed and we need to clean out old maintainer entries
        package.maintainers = maintainers # TODO: Retain order to know who is primary; retain description associated with the maintainership

        # 3.1. refresh versions
        pkg_versions = {pkgver.version: pkgver for pkgver in package.versions}
        for version in pkg['versions']:
            if version['version'] not in pkg_versions:
                pkgver = PackageVersion(version=version['version'],
                                        package=package)
                db.session.add(pkgver)
            else:
                pkgver = pkg_versions[version['version']]

            pkg_keywords = {kwd.name: kwd for kwd in pkgver.keywords}

            # 4.1. synchronize new keywords
            for keyword in version['keywords']:
                if keyword in pkg_keywords:
                    continue

                # TODO: keywords should be initialized earlier to not have to
                # worry about their existence here
                if keyword not in all_keywords:
                    kwd = Keyword(name=keyword)
                    db.session.add(kwd)
                    all_keywords[keyword] = kwd

                pkgver.keywords.append(all_keywords[keyword])

            # 4.2. cleanup removed keywords
            for keyword, kwd_obj in pkg_keywords.items():
                if keyword not in version['keywords']:
                    db.session.delete(kwd_obj)

        # 3.2 cleanup dead revisions
        for version, ver_obj in pkg_versions.items():
            if version not in pkg['versions']:
                db.session.delete(ver_obj)

        # 5. mark package as refreshed
        package.last_sync_ts = now

        if not cnt % 100:
            print("%d packages updated, committing DB transaction" % cnt)
            db.session.commit()
            now = datetime.utcnow()

    db.session.commit()
