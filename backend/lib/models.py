from datetime import datetime
from .. import db


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(30), unique=True, nullable=False)
    description = db.Column(db.Unicode(500))

    def __repr__(self):
        return "<Category %r>" % self.name

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(128), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('packages', lazy='dynamic'))
    description = db.Column(db.Unicode(500))
    last_sync_ts = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcfromtimestamp(0))

    @property
    def full_name(self):
        return "%s/%s" % (self.category.name, self.name)

    def __repr__(self):
        return "<Package '%s/%s'>" % (self.category.name, self.name)

class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Unicode(128), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    package = db.relationship('Package', backref=db.backref('versions', lazy='dynamic'))

    def __repr__(self):
        return "<PackageVersion '%s/%s-%s'>" % (self.package.category.name, self.package.name, self.version)


maintainer_project_membership_rel_table = db.Table('maintainer_project_membership_rel',
    db.Column('project_id', db.Integer, db.ForeignKey('maintainer.id')),
    db.Column('maintainer_id', db.Integer, db.ForeignKey('maintainer.id')),
)

class Maintainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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

    def __repr__(self):
        return "<Maintainer %s '%s'>" % ("project" if self.is_project else "individual", self.email)
