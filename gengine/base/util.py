import datetime
import pytz

class DictObjectProxy:

    def __init__(self, obj={}):
        super().__setattr__("obj",obj)

    def __getattr__(self, name):
        if not name in super().__getattribute__("obj"):
            raise AttributeError
        return super().__getattribute__("obj")[name]

    def __setattr__(self, key, value):
        super().__getattribute__("obj")[key] = value


class Proxy(object):
    def __init__(self):
        self.target = None

    def __getattr__(self, name):
        return getattr(self.target, name)

    def __setattr__(self, name, value):
        if name == "target":
            return object.__setattr__(self, name, value)
        else:
            setattr(self.target, name, value)

    def __call__(self, *args, **kwargs):
        return self.target(*args, **kwargs)


def dt_now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

def dt_ago(**kw):
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc) - datetime.timedelta(**kw)

def dt_in(**kw):
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc) + datetime.timedelta(**kw)

def seconds_until_end_of_day(timezone):
    tzobj = pytz.timezone(timezone)
    now = datetime.datetime.now(tzobj)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + datetime.timedelta(days=1)
    return int((tomorrow - today).total_seconds())

def normalize_key(key):
    return '' if key is None else str(key)

def rowproxy2dict(rp):
    return {k: v for k, v in dict(rp).items() if not str(k).startswith("_")}

def lstrip_word(text, word):
    return text[len(word):] if text[:len(word)] == word else text
