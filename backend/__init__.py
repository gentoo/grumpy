from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask("frontend") # FIXME: Finish rearranging frontend/backend modules properly instead of pretending to be frontend in backend/__init__ because jinja templates are looked for from <what_is_passed_here>/templates
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///../backend/grumpy.db" # FIXME: configuration support; weird ../ because of claiming we are "frontend" to Flask and want to keep the path the same it was before for now. But this problem should go away with config, at least for postgres :)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Change me, you fool'
db = SQLAlchemy(app)

from frontend import *

GrumpyView.register(app)
SetupView.register(app)

__all__ = ["app", "db"]
