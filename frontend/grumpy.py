from flask import render_template, request
from flask_classy import FlaskView

from backend.lib import models


class GrumpyView(FlaskView):
    route_base='/'

    def index(self):
        categories = models.Category.query.all()
        return render_template("index.html", categories=categories)
