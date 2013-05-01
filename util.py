# -*- coding: utf-8 -*-
"""
	project............: meat-a
	description........: web application for sharing meta information
	date...............: 04/2013
	copyright..........: Sebastian Fedrau

	Permission is hereby granted, free of charge, to any person obtaining
	a copy of this software and associated documentation files (the
	"Software"), to deal in the Software without restriction, including
	without limitation the rights to use, copy, modify, merge, publish,
	distribute, sublicense, and/or sell copies of the Software, and to
	permit persons to whom the Software is furnished to do so, subject to
	the following conditions:

	The above copyright notice and this permission notice shall be
	included in all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
	EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
	MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
	IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
	OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
	ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
	OTHER DEALINGS IN THE SOFTWARE.

	This synchronziation procedure works only file-based. It will not upload
	empty folders or remove empty folders on the remote site.
"""

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
		if t is int or t is long:
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

		t = type(obj)

		if t is list or t is tuple:
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

def to_bool(obj):
	t = type(obj)

	if t is bool:
		return obj

	if t is str or t is unicode:
		if obj.lower() == "true":
			return True
		else:
			return False

	return bool(obj)

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
