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
#  @file validators.py
#  Various functions used to validate values.

## @package validators
#  Various functions used to validate values.

import re, util, os, uuid
from PIL import Image
from config import LANGUAGES

## Regex used to validate usernames.
username_regex = re.compile("^\w[\w\-\.]{1,15}$", re.IGNORECASE|re.UNICODE)
## Regex used to validate email addresses.
email_regex = re.compile("^[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{2,4}$", re.IGNORECASE|re.UNICODE)
## Regex used to validate passwords.
password_regex = re.compile("^[\w%s]{8,32}$" % re.escape("!\"§$%&/()=?`´'*#+-_,.;:<>|"), re.IGNORECASE|re.UNICODE)
## Regex used to validate names (e.g. firstname or lastname).
name_regex = re.compile("^.{0,32}$", re.IGNORECASE|re.UNICODE)
## Regex used to validate tags.
tag_regex = re.compile("^\w[\w\-\.]{2,31}$", re.IGNORECASE|re.UNICODE)

## Validates a string using a given regex.
#  @param regex a regular expression
#  @param value string to validate
#  @return True if regex.match() succeeds, the specified string is stripped automatically
def validate_string(regex, value):
	value = util.strip(value)

	if not regex.match(value) is None:
		return True

	return False

## Validates a username.
#  @param username username to validate
#  @return True if the username is valid
def validate_username(username):
	return validate_string(username_regex, username)

## Validates an email address.
#  @param email email address to validate
#  @return True if the email address is valid
def validate_email(email):
	return validate_string(email_regex, email)

## Validates a password.
#  @param password password to validate
#  @return True if the password is valid
def validate_password(password):
	return validate_string(password_regex, password)

## Validates firstname of a user.
#  @param name firstname to validate
#  @return True if the firstname is valid
def validate_firstname(name):
	return validate_string(name_regex, name)

## Validates lastname of a user.
#  @param name lastname to validate
#  @return True if the lastname is valid
def validate_lastname(name):
	return validate_string(name_regex, name)

## Validates gender of a user.
#  @param gender gender to validate
#  @return True if the gender is valid
def validate_gender(gender):
	return gender is None or gender in ["male", "female", "trans man", "trans woman"]

## Validates a comment.
#  @param text text to validate
#  @return True if the comment is valid
def validate_comment(text):
	length = len(util.strip(text))

	if length == 0 or length > 512:
		return False

	return True

## Validates a guid.
#  @param guid guid to test
#  @return True if the guid is valid
def validate_guid(guid):
	if type(guid) is uuid.UUID:
		return True

	try:
		parsed = uuid.UUID(str(guid))
		success = True

	except:
		success = False

	return success

## Validates a tag.
#  @param tag tag to validate
#  @return True if the tag is valid
def validate_tag(tag):
	return validate_string(tag_regex, tag)

## Validates a language.
#  @param language language to validate
#  @return True if the language is valid
def validate_language(language):
	if language is None:
		return True

	return language in LANGUAGES

## Validates an image.
#  @param filename filename of the image
#  @param max_file_size maximum file size
#  @param max_width maximum width of the image
#  @param max_height maximum height of the image
#  @param formats array holding allowed image formats (e.g. [ "PNG", "JPEG" ])
#  @return True if the image is valid
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
