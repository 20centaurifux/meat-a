# -*- coding: utf-8 -*-

from time import mktime
from datetime import datetime
from hashlib import sha1
from bson import json_util
import random, string, json

def now():
	now = datetime.utcnow()

	return mktime(now.timetuple()) * 1000 + now.microsecond / 1000

def hash(plain):
	m = sha1()
	m.update(plain)

	return m.hexdigest()

def generate_junk(length, characters = None):
	if characters is None:
		characters = string.ascii_letters + string.digits

	result = []

	for i in range(length):
		index = random.randint(0, len(characters) - 1)
		result.append(characters[index])

	random.shuffle(result)

	return "".join(result)

def to_json(obj):
	return json.dumps(obj, sort_keys = True, default = json_util.default)

def enum(**enums):
    return type('Enum', (), enums)

def strip(text):
	if text is None:
		text = ""

	return text.strip()
