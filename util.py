# -*- coding: utf-8 -*-

from time import mktime
from datetime import datetime
from hashlib import sha1, sha256
from bson import json_util
import random, string, json, os, hmac

def now():
	now = datetime.utcnow()

	return mktime(now.timetuple()) * 1000 + now.microsecond / 1000

def unix_timestamp():
	now = datetime.utcnow()

	return int(mktime(now.timetuple()))

def hash(plain):
	m = sha256()
	m.update(plain)

	return m.hexdigest()

def hash_file(filename, hasher, block_size = 81920):
	stream = open(filename, "rb")

	for bytes in read_from_stream(stream, block_size):
		hasher.update(bytes)

	stream.close()

	return hasher.hexdigest()

def sign_message(secret, **kwargs):
	def serialize(value):
		t = type(value)

		if value is None:
			return "null"
		if t is int:
			return str(value)
		elif t is str:
			return value
		elif t is unicode:
			return value.encode("utf-8")
		elif t is bool:
			return str(value).lower()
		else:
			raise Exception("Invalid parameter type: %s" % type(value))

	if type(secret) is unicode:
		secret = secret.encode("utf-8")

	h = hmac.new(secret, "", sha1)

	for key in sorted(kwargs.keys(), key = lambda k: k.upper()):
		obj = kwargs[key]

		if type(obj) is list or type(obj) is tuple:
			for value in obj:
				h.update(serialize(value))
		else:
			h.update(serialize(obj))

	return h.hexdigest()

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

def remove_all_files(directory):
	for file in os.listdir(directory):
		path = os.path.join(directory, file)
		os.remove(path)

def read_from_stream(stream, block_size = 81920, max_size = None):
	bytes = stream.read(block_size)
	total = len(bytes)

	while len(bytes) > 0:
		yield bytes

		bytes = stream.read(block_size)
		total += len(bytes)

		if not max_size is None and total > max_size:
			from exception import StreamExceedsMaximumException

			raise StreamExceedsMaximumException()
