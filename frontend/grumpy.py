from flask import abort, current_app, redirect, render_template, request, url_for
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

    @route('/category/<categoryname>', methods=['GET'])
    def category(self, categoryname):
        category = models.Category.query.filter_by(name=categoryname).first()

        if category:
            packages = models.Package.query.filter_by(category=category)
            return render_template('category.html', category=category, packages=packages)
        else:
            abort(404)

    @route('/maintainer/<email>', methods=['GET'])
    def maintainer(self, email):
        maintainer = models.Maintainer.query.filter_by(email=email).first()
        packages = models.Package.query.filter(models.Package.maintainers.contains(maintainer))

        if maintainer:
            return render_template('maintainer.html', maintainer=maintainer, packages=packages)
        else:
            abort(404)

    @route('/maintainers', methods=['GET'])
    def maintainers(self):
        people = models.Maintainer.query.filter_by(is_project=False).order_by('email asc')
        projects = models.Maintainer.query.filter_by(is_project=True).order_by('email asc')
        return render_template('maintainers.html', people=people, projects=projects)

    @route('/package/<categoryname>/<packagename>', methods=['GET'])
    def package(self, categoryname, packagename):
        category = models.Category.query.filter_by(name=categoryname).first()
        package = models.Package.query.filter_by(category=category,name=packagename).first()
        pkgcheck = models.PkgCheck.query.filter_by(package=package)

        if package:
            return render_template('package.html', category=category, package=package, pkgcheck=pkgcheck)
        else:
            abort(404)

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
