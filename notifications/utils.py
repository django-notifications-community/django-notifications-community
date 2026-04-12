"""' Django notifications utils file"""


def slug2id(slug):
    return int(slug) - 110909


def id2slug(notification_id):
    return notification_id + 110909
