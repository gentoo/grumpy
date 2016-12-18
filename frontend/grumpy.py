from flask import current_app, redirect, render_template, request, url_for
from flask_classy import FlaskView, route
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

class SetupView(FlaskView):
    @route('/', methods=['GET', 'POST']) # FIXME: Can we enable POST without giving a rule override from the automatic, or handle this some other better way with wtforms setup?
    def index(self):
        maintainers = models.Maintainer.query.order_by(collate(models.Maintainer.email, 'NOCASE')).all()
        form = FollowSetupForm()
        choices = []
        defaults = []
        form_mapping = {}
        follows = request.cookies.get('follows', '').split()
        for maintainer in maintainers:
            choices.append((maintainer.id, maintainer.email))
            form_mapping[maintainer.id] = maintainer
            if maintainer.email in follows:
                defaults.append(maintainer.id)

        form.maintainers.choices = choices
        form.maintainers.default = defaults

        if form.validate_on_submit():
            followed_maintainers = set()
            for choice in choices:
                if choice[0] in form.maintainers.data:
                    followed_maintainers.add(choice[1])
            response = current_app.make_response(redirect(url_for('GrumpyView:index')))
            # FIXME: This will fail with too many following (usually string value length above 4093); move this to session eventually. If that is delayed, we could at least make it fit more by omitting @gentoo.org in those cases (and suffixing it back after cookie read for defaults handling)
            response.set_cookie('follows', value=' '.join(followed_maintainers))
            return response

        form.process()

        return render_template("setup.html", mapping=form_mapping, form=form)
