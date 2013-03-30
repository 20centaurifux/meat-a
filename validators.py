# -*- coding: utf-8 -*-
import re, util, os
from PIL import Image

username_regex = re.compile("^\w[\w\-\.]{1,15}$", re.IGNORECASE | re.UNICODE)
email_regex = re.compile("^[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{2,4}$", re.IGNORECASE | re.UNICODE)
password_regex = re.compile("^[\w%s]{8,32}$" % re.escape("!\"§$%&/()=?`´'*#+-_,.;:<>|"), re.IGNORECASE | re.UNICODE)
name_regex = re.compile("^.{0,32}$", re.IGNORECASE | re.UNICODE)

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
