from flask import render_template, request
from flask_classy import FlaskView
from sqlalchemy.sql import collate
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, widgets


from backend.lib import models


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class FollowSetupForm(FlaskForm):
    maintainers = MultiCheckboxField('Followed maintainers', coerce=int)

class GrumpyView(FlaskView):
    route_base='/'

    def index(self):
        categories = models.Category.query.all()
        return render_template("index.html", categories=categories)

    def setup(self):
        maintainers = models.Maintainer.query.order_by(collate(models.Maintainer.email, 'NOCASE')).all()
        form = FollowSetupForm()
        choices = []
        form_mapping = {}
        for maintainer in maintainers:
            choices.append((maintainer.id, maintainer.email))
            form_mapping[maintainer.id] = maintainer

        form.maintainers.choices = choices
        form.process()

        return render_template("setup.html", mapping=form_mapping, form=form)
