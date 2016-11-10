#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_script import Manager, Shell

from backend import app, db
from backend.lib import sync


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
    """Synchronize Gentoo data from packages.gentoo.org API"""
    sync.sync_categories()
    sync.sync_packages()
    #sync_versions()

@manager.command
def sync_categories():
    """Synchronize only Gentoo categories data"""
    sync.sync_categories()

@manager.command
def sync_packages():
    """Synchronize only Gentoo packages base data (without details)"""
    sync.sync_packages()

@manager.command
def sync_versions():
    """Synchronize only Gentoo package details"""
    sync.sync_versions()

if __name__ == '__main__':
    manager.run()
