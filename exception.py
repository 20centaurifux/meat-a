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

import util

ErrorCode = util.enum(SUCCESS = 0,
                      INTERNAL_FAILURE = 1,
                      STREAM_EXCEEDS_MAXIMUM = 2,
                      INVALID_REQUEST = 3,
                      AUTHENTICATION_FAILED = 4,
                      REQUEST_EXPIRED = 5,
                      CONSTRAINT_VIOLOATION = 100,
                      INVALID_PARAMETER = 200,
                      USER_ALREADY_EXISTS = 300,
                      COULD_NOT_FIND_USER = 301,
                      USER_IS_BLOCKED = 302,
                      USERNAME_ALREADY_REQUESTED = 303,
                      EMAIL_ALREADY_ASSIGNED = 304,
                      INVALID_REQUEST_CODE = 305,
                      INVALID_PASSWORD = 306,
                      INVALID_EMAIL_ADDRESS = 307,
                      INVALID_IMAGE_FORMAT = 400,
                      OBJECT_IS_LOCKED = 500,
                      OBJECT_NOT_FOUND = 501,
                      USER_ALREADY_RATED = 502,
                      HTTP_FAILURE = 600)

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

class InvalidRequestException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_REQUEST, "The received request is invalid.")

class AuthenticationFailedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.AUTHENTICATION_FAILED, "Authentication failed.")

class RequestExpiredException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.REQUEST_EXPIRED, "Request expired.")

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

class InvalidEmailAddressException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_EMAIL_ADDRESS, "Invalid email address.")

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

class HttpException(Exception):
	def __init__(self, http_status, message):
		Exception.__init__(self, ErrorCode.HTTP_FAILURE, message)
		self.http_status = http_status
