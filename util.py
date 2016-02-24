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
"""

##
#  @file util.py
#  Utility functions.

## @package util
#  Utility functions.

from time import mktime
from datetime import datetime
from hashlib import sha256
from bson import json_util
from urllib2 import quote
import random, string, json, uuid, os

## Gets the current timestamp (UTC) in milliseconds.
#  @return a float
def now():
	now = datetime.utcnow()

	return mktime(now.timetuple()) * 1000 + now.microsecond / 1000

## Calculates the checksum of a string.
#  @param plain a string
#  @return checksum as hex-string
def hash(plain):
	m = sha256()
	m.update(plain)

	return m.hexdigest()

## Calculates the password hash.
#  @param plain plain password
#  @param salt password salt
#  @return checksum as hex-string
def password_hash(plain, salt):
	m = sha256()
	m.update("%s%s" % (salt, plain))

	return m.hexdigest()

## Reads data from a stream and computes its hash.
#  @param stream a stream to read data from
def stream_hash(stream):
	m = sha256()

	map(lambda b: m.update(b), read_from_stream(stream))

	return m.hexdigest()

## Generates a guid.
def new_guid():
	return str(uuid.uuid4())

## Generates a random string.
#  @param length length of the generated string
#  @param characters characters which should be used to generate the string - if this
#                    parameter has not been specified string.ascii_letters + string.digits
#                    will be used
#  @return a string
def generate_junk(length, characters = None):
	if characters is None:
		characters = string.ascii_letters + string.digits

	result = []

	for i in xrange(length):
		index = random.randint(0, len(characters) - 1)
		result.append(characters[index])

	random.shuffle(result)

	return "".join(result)

## Converts an object to JSON.
#  @param obj object to serialize
#  @return a JSON string
def to_json(obj):
	return json.dumps(obj, sort_keys = True, default = json_util.default)

## Generates an enumeration.
#  @param enums definition of the enumeration
#  @return a new enumeration
def enum(**enums):
    return type('Enum', (), enums)

## Returns a copy of a string without leading and trailing whitespace. When None is
#  specified an empty string is returned.
#  @param text text to create copy of
#  @return a new string
def strip(text):
	if text is None:
		text = ""

	return text.strip()

## Converts an object to bool.
#  @param obj an object
#  @return True or False
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

## Builds an URL.
#  @param fmt a format string
#  @param url an url
#  @param params parameters to quote
#  @return an url with quoted parameters
def build_url(fmt, url, *params):
	return url + fmt % tuple(map(quote, params))

## Generator to read blocks from an input stream.
#  @param stream input stream
#  @param block_size size of blocks read from stream
#  @param max_size if the stream exceeds max_size an exception.StreamExceedsMaximumException
#                  will be thrown
#  @return read bytes
def read_from_stream(stream, block_size=81920, max_size=None):
	bytes = stream.read(block_size)
	total = len(bytes)

	while len(bytes) > 0:
		yield bytes

		bytes = stream.read(block_size)
		total += len(bytes)

		if not max_size is None and total > max_size:
			from exception import StreamExceedsMaximumException
			raise StreamExceedsMaximumException()

## Selects values from a dictionary using a specified key collection.
#  @param m a dictionary
#  @param keys sequence of keys
#  @return an array containing the selected values.
def select_values(m, keys):
	def get(m, k):
		try:
			v = m[k]

		except KeyError:
			v = None

		return v

	return map(lambda k: get(m, k), keys)

## Splits a string and returns a set of stripped tokens.
#  @param str string to split
#  @param sep the separator
#  @return a set of token
def split_strip_set(str, sep):
	s = set()

	for token in filter(lambda t: len(t) > 0, map(lambda t: t.strip(), str.split(sep))):
		s.add(token)

	return s

## Gets a random element from an array.
#  @param arr an array
#  @return an array element
def pick_one(arr):
	return arr[random.randint(0, len(arr) - 1)]

## An iterator for reading data from a stream lazily.
class StreamReader:
	## The constructor.
	#  @param stream stream to read data from
	#  @param buffer_size number of bytes read on each iteration
	def __init__(self, stream, buffer_size=81920):
		self.__size = self.__get_stream_length__(stream)
		self.__buffer_size = buffer_size
		self.__generator = self.__create_generator__(stream)
		self.__stream = stream

	def __get_stream_length__(self, stream):
		pos = stream.tell()
		stream.seek(0, os.SEEK_END)
		size = stream.tell()
		stream.seek(pos, os.SEEK_SET)

		return int(size)

	def __len__(self):
		return self.__size

	def __iter__(self):
		return self.__generator

	def __del__(self):
		if not self.__stream is None:
			self.__stream.close()
			self.__stream = None

	def __create_generator__(self, stream):
		while True:
			bytes = stream.read(self.__buffer_size)

			if bytes is None or len(bytes) == 0:
				self.__size = 0
				break

			yield bytes

## Creates a StreamReader reading data from the specified file.
#  @param filename name of the file to open
#  @param mode file mode
#  @param block_size number of bytes read on each operation
#  @return a new StreamReader
def read_file(filename, mode="rb", block_size=81920):
	f = open(filename, mode)

	return StreamReader(f, block_size)
