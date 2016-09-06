from flask import json
import requests
from .. import app, db
from .models import Category

http_session = requests.session()

def sync_categories():
    url = "https://packages.gentoo.org/categories.json"
    data = http_session.get(url)
    categories = json.loads(data.text)
    existing_categories = {}
    for cat in Category.query.all():
        existing_categories[cat.name] = cat
    for category in categories:
        if category['name'] in existing_categories:
            existing_categories[category['name']].description = category['description']
        else:
            new_cat = Category(name=category['name'], description=category['description'])
            db.session.add(new_cat)
    db.session.commit()
