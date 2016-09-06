#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_script import Manager, Shell

from backend import app


manager = Manager(app)

def shell_context():
    return dict(app=manager.app)

manager.add_command('shell', Shell(make_context=shell_context))

if __name__ == '__main__':
    manager.run()
