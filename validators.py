# -*- coding: utf-8 -*-
import re

username_regex = re.compile("^\w[\w\-\.]{1,15}$", re.IGNORECASE | re.UNICODE)
email_regex = re.compile("^[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{2,4}$", re.IGNORECASE | re.UNICODE)

def validate_string(regex, value):
	if value is None:
		value = ""

	value = value.strip()

	if not regex.match(value) is None:
		return True

	return False

def validate_username(username):
	return validate_string(username_regex, username)

def validate_email(email):
	return validate_string(email_regex, email)
