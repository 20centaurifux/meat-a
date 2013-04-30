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

import re, util, os
from PIL import Image
from config import LANGUAGES

username_regex = re.compile("^\w[\w\-\.]{1,15}$", re.IGNORECASE | re.UNICODE)
email_regex = re.compile("^[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{2,4}$", re.IGNORECASE | re.UNICODE)
password_regex = re.compile("^[\w%s]{8,32}$" % re.escape("!\"§$%&/()=?`´'*#+-_,.;:<>|"), re.IGNORECASE | re.UNICODE)
name_regex = re.compile("^.{0,32}$", re.IGNORECASE | re.UNICODE)
tag_regex = re.compile("^\w[\w\-\.]{2,15}$", re.IGNORECASE | re.UNICODE)

def validate_string(regex, value):
	value = util.strip(value)

	if not regex.match(value) is None:
		return True

	return False

def validate_username(username):
	return validate_string(username_regex, username)

def validate_email(email):
	return validate_string(email_regex, email)

def validate_password(password):
	return validate_string(password_regex, password)

def validate_firstname(name):
	return validate_string(name_regex, name)

def validate_lastname(name):
	return validate_string(name_regex, name)

def validate_gender(gender):
	return gender is None or gender == "m" or gender == "f"

def validate_comment(text):
	length = len(util.strip(text))

	if length == 0 or length > 512:
		return False

	return True

def validate_tag(tag):
	return validate_string(tag_regex, tag)

def validate_language(language):
	if language is None:
		return True

	return language in LANGUAGES

def validate_image_file(filename, max_file_size, max_width, max_height, formats):
	img = Image.open(filename)
	info = os.stat(filename)

	if info.st_size > max_file_size:
		return False

	if img.size[0] > max_width or img.size[1] > max_height:
		return False

	if not img.format in formats:
		return False

	return True
