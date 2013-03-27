# -*- coding: utf-8 -*-
import re, util

username_regex = re.compile("^\w[\w\-\.]{1,15}$", re.IGNORECASE | re.UNICODE)
email_regex = re.compile("^[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{2,4}$", re.IGNORECASE | re.UNICODE)
password_regex = re.compile("^[\w%s]{8,32}$" % re.escape("!\"§$%&/()=?`´'*#+-_,.;:<>|"), re.IGNORECASE | re.UNICODE)
name_regex = re.compile("^[.*]{0,32}$", re.IGNORECASE | re.UNICODE)

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
