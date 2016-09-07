from flask import json
import requests
from .. import app, db
from .models import Category, Package

url_base = "https://packages.gentoo.org/"
http_session = requests.session()

def sync_categories():
    url = url_base + "categories.json"
    data = http_session.get(url)
    # TODO: Handle response error (if not data)
    categories = json.loads(data.text)
    existing_categories = {}
    # TODO: Use UPSERT instead (on_conflict_do_update) if we can rely on postgresql:9.5
    for cat in Category.query.all():
        existing_categories[cat.name] = cat
    for category in categories:
        if category['name'] in existing_categories:
            existing_categories[category['name']].description = category['description']
        else:
            new_cat = Category(name=category['name'], description=category['description'])
            db.session.add(new_cat)
    db.session.commit()

def sync_packages():
    for category in Category.query.all():
        existing_packages = category.packages.all()
        print("Existing packages in DB for category %s: %s" % (category.name, existing_packages,))
        data = http_session.get(url_base + "categories/" + category.name + ".json")
        if not data:
            print("No JSON data for category %s" % category.name) # FIXME: Better handling; mark category as inactive/gone?
            continue
        packages = json.loads(data.text)['packages']
        # TODO: Use UPSERT instead (on_conflict_do_update)
        existing_packages = {}
        for pkg in Package.query.all():
            existing_packages[pkg.name] = pkg
        for package in packages:
            if package['name'] in existing_packages:
                continue # TODO: Update description once we keep that in DB
            else:
                new_pkg = Package(category_id=category.id, name=package['name'])
                db.session.add(new_pkg)
    db.session.commit()
