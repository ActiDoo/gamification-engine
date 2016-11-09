import names
import random

from gengine.app.model import User, Language
from gengine.metadata import DBSession

default_gen_data = {
    "timezone" : "Europe/Berlin",
    "area" : {
        "min_lat" : 51.65,
        "max_lat" : 51.75,
        "min_lng" : 8.70,
        "max_lng" : 8.79
    },
    "country" : "DE",
    "region" : "NRW",
    "city" : "Paderborn",
    "language" : "de"
}

alt_gen_data = {
    "timezone" : "US/Eastern",
    "area" : {
        "min_lat" : 40.680,
        "max_lat" : 40.780,
        "min_lng" : -73.89,
        "max_lng" : -73.97
    }
}

class Undefined():
    pass

undefined = Undefined()

def randrange_float(f1,f2):
    return random.random() * abs(f1 - f2) + min(f1,f2)

def create_user(
        user_id = undefined,
        lat = undefined,
        lng = undefined,
        country = undefined,
        region = undefined,
        city = undefined,
        timezone = undefined,
        language = undefined,
        friends = [],
        groups = [],
        additional_public_data = undefined,
        gen_data = default_gen_data
    ):

    if additional_public_data is undefined:
        additional_public_data = {
            'first_name' : names.get_first_name(),
            'last_name' : names.get_last_name()
        }

    if user_id is undefined:
        user_id = (DBSession.execute("SELECT max(id) as c FROM users").scalar() or 0) + 1

    if lat is undefined:
        lat = randrange_float(gen_data["area"]["min_lat"],gen_data["area"]["max_lat"])

    if lng is undefined:
        lng = randrange_float(gen_data["area"]["min_lng"], gen_data["area"]["max_lng"])

    if country is undefined:
        country = gen_data["country"]

    if timezone is undefined:
        timezone = gen_data["timezone"]

    if region is undefined:
        region = gen_data["region"]

    if city is undefined:
        city = gen_data["city"]

    if language is undefined:
        language = gen_data["language"]

    User.set_infos(
        user_id = user_id,
        lat = lat,
        lng = lng,
        timezone = timezone,
        country = country,
        region = region,
        city = city,
        language = language,
        groups = groups,
        friends = friends,
        additional_public_data = additional_public_data
    )

    return User.get_user(user_id)

def get_or_create_language(name):
    lang = DBSession.query(Language).filter_by(name=name).first()
    if not lang:
        lang = Language()
        lang.name = name
        DBSession.add(lang)
        DBSession.flush()
    return lang