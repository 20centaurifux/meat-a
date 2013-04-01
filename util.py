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

def hash_file(filename, hasher, blocksize = 65536):
	stream = open(filename, "rb")
	buffer = stream.read(blocksize)

	while len(buffer) > 0:
		hasher.update(buffer)
		buffer = stream.read(blocksize)

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
