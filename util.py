from time import mktime
from datetime import datetime
from hashlib import sha1
from bson import json_util
import random, string, json

def now():
	return mktime(datetime.utcnow().timetuple())

def hash(plain):
	m = sha1()
	m.update(plain)

	return m.hexdigest()

def generate_junk(length, characters = None):
	if characters is None:
		characters = string.ascii_letters + string.digits

	random.seed()

	result = []

	for i in range(length):
		index = random.randint(0, len(characters) - 1)
		result.append(characters[index])

	return "".join(result)

def to_json(obj):
	return json.dumps(obj, sort_keys = True, default = json_util.default)
