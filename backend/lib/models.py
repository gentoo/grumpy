from datetime import datetime
from .. import db


class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # current longest entries would be of length 16 with "~sparc64-freebsd" and "~sparc64-solaris"
    name = db.Column(db.Unicode(20), unique=True, nullable=False) # TODO: Force lower case?

    @property
    def stable(self):
        return not self.name.startswith('~')

    def __repr__(self):
        return "<Keyword %r>" % self.name

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(30), unique=True, nullable=False)
    description = db.Column(db.Unicode(500))

    def __repr__(self):
        return "<Category %r>" % self.name

package_maintainer_rel_table = db.Table('package_maintainer_rel',
    db.Column('package_id', db.Integer, db.ForeignKey('package.id')),
    db.Column('maintainer_id', db.Integer, db.ForeignKey('maintainer.id')),
)

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(128), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('packages', lazy='select'))
    description = db.Column(db.Unicode(500))
    last_sync_ts = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcfromtimestamp(0))
    maintainers = db.relationship("Maintainer",
        secondary=package_maintainer_rel_table,
        backref='directly_maintained_packages')
    # versions backref

    @property
    def full_name(self):
        return "%s/%s" % (self.category.name, self.name)

    def __repr__(self):
        return "<Package '%s/%s'>" % (self.category.name, self.name)

package_version_keywords_rel_table = db.Table('package_version_keywords_rel',
    db.Column('package_version_id', db.Integer, db.ForeignKey('package_version.id')),
    db.Column('keyword_id', db.Integer, db.ForeignKey('keyword.id')),
)

class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Unicode(128), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    package = db.relationship('Package', backref=db.backref('versions', lazy='select'))
    keywords = db.relationship("Keyword", secondary=package_version_keywords_rel_table)
    masks = db.Column(db.UnicodeText, nullable=True) # Concatenated mask reasons if p.masked, NULL if not a masked version. TODO: arch specific masks

    def __repr__(self):
        return "<PackageVersion '%s/%s-%s'>" % (self.package.category.name, self.package.name, self.version)


maintainer_project_membership_rel_table = db.Table('maintainer_project_membership_rel',
    db.Column('project_id', db.Integer, db.ForeignKey('maintainer.id')),
    db.Column('maintainer_id', db.Integer, db.ForeignKey('maintainer.id')),
)

class Maintainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # TODO: This has to be unique case insensitive. Currently we have to always force lower() to guarantee this and find the proper maintainer entry; later we might want to use some sort of NOCASE collate rules here to keep the capitalization as preferred per master data
    email = db.Column(db.Unicode(50), nullable=False, unique=True)
    is_project = db.Column(db.Boolean, nullable=False, server_default='f', default=False)
    name = db.Column(db.Unicode(128))
    url = db.Column(db.Unicode())
    description = db.Column(db.Unicode(500))

    members = db.relationship("Maintainer",
        secondary=maintainer_project_membership_rel_table,
        primaryjoin=id==maintainer_project_membership_rel_table.c.project_id,
        secondaryjoin=id==maintainer_project_membership_rel_table.c.maintainer_id,
        backref='projects')
    # projects relationship backref ^^
    # directly_maintained_packages backref - list of packages maintained directly by given project or individual maintainer (as opposed to a bigger list that includes packages maintained by parent/child projects or projects the given individual maintainer is part of)

    def __repr__(self):
        return "<Maintainer %s '%s'>" % ("project" if self.is_project else "individual", self.email)
