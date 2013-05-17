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
#  @file exception.py
#  Exceptions and error codes.

## @package exception
#  Exceptions and error codes.

import util

## Enumeration indicating error types.
ErrorCode = util.enum(SUCCESS = 0,
                      INTERNAL_FAILURE = 1,
                      STREAM_EXCEEDS_MAXIMUM = 2,
                      INVALID_REQUEST = 3,
                      AUTHENTICATION_FAILED = 4,
                      REQUEST_EXPIRED = 5,
                      TOO_MANY_REQUESTS = 6,
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

## Exception base class.
class Exception:
	## The constructor.
	#  @param code error code
	#  @param message a message
	def __init__(self, code, message):
		## Error code of the exception.
		self.code = code
		## String describing the exception.
		self.message = message

## Exception used for internal failures.
class InternalFailureException(Exception):
	## The constructor.
	#  @param message message describing the exception
	def __init__(self, message):
		Exception.__init__(self, ErrorCode.INTERNAL_FAILURE, message)

## Exception raised when a stream exceeds the allowed maximum length.
class StreamExceedsMaximumException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.STREAM_EXCEEDS_MAXIMUM, "The stream exceeds the defined maximum length.")

## Exception raised when a request is invalid (e.g. when the checksum is wrong).
class InvalidRequestException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_REQUEST, "The received request is invalid.")

## Exception raised when a user is not authorized.
class AuthenticationFailedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.AUTHENTICATION_FAILED, "Authentication failed.")

## Exception raised when the sent timestamp is expired.
class RequestExpiredException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.REQUEST_EXPIRED, "Request expired.")

## Exception raised when the HTTP request limit has been reached.
class TooManyRequestsException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.TOO_MANY_REQUESTS, "Too many requests.")

## Exception raised when there's a constraint violation on database level.
class ConstraintViolationException(Exception):
	## The constructor.
	#  @param message message describing the exception
	def __init__(self, message):
		Exception.__init__(self, ErrorCode.CONSTRAINT_VIOLOATION, message)

## Exception raised when a specified parameter is invalid.
class InvalidParameterException(Exception):
	## The constructor.
	#  @param parameter name of the invalid parameter
	def __init__(self, parameter):
		Exception.__init__(self, ErrorCode.INVALID_PARAMETER, "Invalid parameter.")
		## name of the invalid parameter
		self.parameter = parameter

## Exception raised when a user cannot be created because the username already exists.
class UserAlreadyExistsException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USER_ALREADY_EXISTS, "The given username does already exist.")

## Exception raised when a user is blocked and is not allowed to perform an activity.
class UserIsBlockedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USER_IS_BLOCKED, "User is blocked.")

## Exception raised when a specified user cannot be found.
class UserNotFoundException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.COULD_NOT_FIND_USER, "Username not found.")

## Exception raised when a user account cannot be requested because a request for the given username already exists.
class UsernameAlreadyRequestedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USERNAME_ALREADY_REQUESTED, "The given username has already been requested.")

## Exception raised when an email address is already assigned.
class EmailAlreadyAssignedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.EMAIL_ALREADY_ASSIGNED, "The given email address is already in use.")

## Exception raised when a specified request code is invalid.
class InvalidRequestCodeException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_REQUEST_CODE, "Invalid request code.")

## Exception raised when a specified password is invalid.
class InvalidPasswordException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_PASSWORD, "Invalid password.")

## Exception raised when a specified email address is invalid.
class InvalidEmailAddressException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_EMAIL_ADDRESS, "Invalid email address.")

## Exception raised when the format of an image is invalid.
class InvalidImageFormatException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_IMAGE_FORMAT, "The given image has an invalid format.")

## Exception raised when an object cannot be modified because it's locked.
class ObjectIsLockedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.OBJECT_IS_LOCKED, "The given object is locked.")

## Exception raised when an object cannot be found.
class ObjectNotFoundException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.OBJECT_NOT_FOUND, "Object not found.")

## Exception raised when a user has already rated for an object.
class UserAlreadyRatedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USER_ALREADY_RATED, "The user has already rated for the given object.")

## Exception used for HTTP failures.
class HttpException(Exception):
	## The constructor.
	#  @param http_status the HTTP status code
	#  @param message a failure message
	def __init__(self, http_status, message):
		Exception.__init__(self, ErrorCode.HTTP_FAILURE, message)
		self.http_status = http_status
