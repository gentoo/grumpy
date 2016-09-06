from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///grumpy.db" # FIXME: configuration support
db = SQLAlchemy(app)

from .lib import models


@app.route("/")
def hello_world():
    categories = models.Category.query.all()
    text = ""
    for cat in categories:
        text += "<b>%s</b>: %s<br>" % (cat.name, cat.description)
    return "Hello World! These are the package categories I know about:<br>%s" % text


__all__ = ["app", "db"]
