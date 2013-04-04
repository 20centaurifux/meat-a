# -*- coding: utf-8 -*-

import util

ErrorCode = util.enum(INTERNAL_FAILURE = 0,
                      STREAM_EXCEEDS_MAXIMUM = 1,
                      CONSTRAINT_VIOLOATION = 100,
                      INVALID_PARAMETER = 200,
                      USER_ALREADY_EXISTS = 300,
                      COULD_NOT_FIND_USER = 301,
                      USER_IS_BLOCKED = 302,
                      USERNAME_ALREADY_REQUESTED = 303,
                      EMAIL_ALREADY_ASSIGNED = 304,
                      INVALID_REQUEST_CODE = 305,
                      INVALID_PASSWORD = 306,
                      INVALID_IMAGE_FORMAT = 400,
                      OBJECT_IS_LOCKED = 500,
                      OBJECT_NOT_FOUND = 501,
                      USER_ALREADY_RATED = 502)

class Exception:
	def __init__(self, code, message):
		self.code = code
		self.message = message

class InternalFailureException(Exception):
	def __init__(self, message):
		Exception.__init__(self, ErrorCode.INTERNAL_FAILURE, message)

class StreamExceedsMaximumException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.STREAM_EXCEEDS_MAXIMUM, "The stream exceeds the defined maximum length.")

class ConstraintViolationException(Exception):
	def __init__(self, message):
		Exception.__init__(self, ErrorCode.CONSTRAINT_VIOLOATION, message)
	
class InvalidParameterException(Exception):
	def __init__(self, parameter):
		Exception.__init__(self, ErrorCode.INVALID_PARAMETER, "Invalid parameter.")
		self.parameter = parameter

class UserAlreadyExistsException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USER_ALREADY_EXISTS, "The given username does already exist.")

class UserIsBlockedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USER_IS_BLOCKED, "User is blocked.")

class UserNotFoundException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.COULD_NOT_FIND_USER, "Username not found.")

class UsernameAlreadyRequestedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USERNAME_ALREADY_REQUESTED, "The given username has already been requested.")

class EmailAlreadyAssignedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.EMAIL_ALREADY_ASSIGNED, "The given email address is already in use.")

class InvalidRequestCodeException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_REQUEST_CODE, "Invalid request code.")

class InvalidPasswordException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_PASSWORD, "Invalid password.")

class InvalidImageFormatException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_IMAGE_FORMAT, "The given image has an invalid format.")

class ObjectIsLockedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.OBJECT_IS_LOCKED, "The given object is locked.")

class ObjectNotFoundException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.OBJECT_NOT_FOUND, "Object not found.")

class UserAlreadyRatedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USER_ALREADY_RATED, "The user has already rated for the given object.")

