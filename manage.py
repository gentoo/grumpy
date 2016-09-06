#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_script import Manager, Shell

from backend import app, db
from backend.lib.sync import sync_categories


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
    """Syncronize Gentoo data from packages.gentoo.org API"""
    sync_categories()

if __name__ == '__main__':
    manager.run()
