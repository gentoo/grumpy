#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_script import Manager, Shell

from backend import app, db
from backend.lib import sync

# TODO: Replace this with flask 0.11 "flask" CLI and the extra commands support via click therein - http://flask.pocoo.org/docs/0.11/cli/
# TODO: This would then allow FLASK_DEBUG=1 automatically reloading the server on code changes when launched with "flask run"

manager = Manager(app)

def shell_context():
    return dict(app=manager.app, db=db)

manager.add_command('shell', Shell(make_context=shell_context))

@manager.command
def init():
    """Initialize empty database with tables"""
    db.create_all()

@manager.command
def sync_gentoo():
    """Synchronize Gentoo data"""
    sync.sync_projects()
    sync.sync_categories()
    sync.sync_packages()
    #sync_versions()

@manager.command
def sync_projects():
    """Synchronize only Gentoo projects.xml data"""
    sync.sync_projects()

@manager.command
def sync_categories():
    """Synchronize only Gentoo categories data"""
    sync.sync_categories()

@manager.command
def sync_packages():
    """Synchronize only Gentoo packages base data (without details)"""
    sync.sync_packages()

@manager.command
def sync_pkgcheck():
    """Synchronize dev-util/pkgcheck static analysis data"""
    sync.sync_pkgcheck()

@manager.command
def sync_versions():
    """Synchronize only Gentoo package details"""
    sync.sync_versions()

if __name__ == '__main__':
    manager.run()
