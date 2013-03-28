# -*- coding: utf-8 -*-

import util

ErrorCode = util.enum(CONSTRAINT_VIOLOATION = 0,
                      INVALID_PARAMETER = 100,
                      USER_ALREADY_EXISTS = 200,
                      COULD_NOT_FIND_USER = 201,
                      USER_IS_BLOCKED = 202,
                      USERNAME_ALREADY_REQUESTED = 203,
                      EMAIL_ALREADY_ASSIGNED = 204,
                      INVALID_REQUEST_CODE = 205,
                      INVALID_PASSWORD = 206)

class Exception:
	def __init__(self, code, message):
		self.code = code
		self.message = message

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
