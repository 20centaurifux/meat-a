# -*- coding: utf-8 -*-

from time import mktime
from datetime import datetime
from hashlib import sha256
from bson import json_util
import random, string, json, os

def now():
	now = datetime.utcnow()

	return mktime(now.timetuple()) * 1000 + now.microsecond / 1000

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
