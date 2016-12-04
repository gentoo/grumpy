from flask import render_template, request
from flask_classy import FlaskView
from sqlalchemy.sql import collate

from backend.lib import models


class GrumpyView(FlaskView):
    route_base='/'

    def index(self):
        categories = models.Category.query.all()
        return render_template("index.html", categories=categories)

    def setup(self):
        maintainers = models.Maintainer.query.order_by(collate(models.Maintainer.email, 'NOCASE')).all()
        return render_template("setup.html", maintainers=maintainers)
