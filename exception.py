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
                      INVALID_IMAGE_FORMAT = 3,
		      METHOD_NOT_SUPPORTED = 4,
                      AUTHENTICATION_FAILED = 100,
                      NOT_AUTHORIZED = 101,
                      MISSING_PARAMETER = 102,
                      INVALID_PARAMETER = 200,
		      NOT_FOUND = 201,
		      CONFLICT = 202,
                      INVALID_REQUEST_CODE = 203,
		      USER_NOT_FOUND = 300,
                      USER_IS_BLOCKED = 301,
                      WRONG_PASSWORD = 302,
                      WRONG_EMAIL_ADDRESS = 303,
		      NO_FRIENDSHIP = 304,
                      OBJECT_NOT_FOUND = 400,
                      OBJECT_IS_LOCKED = 401,
		      HTTP_FAILURE = 500)

## Exception base class.
class BaseException:
	## The constructor.
	#  @param code error code
	#  @param http_status a mapped HTTP status
	#  @param message a descripton of the exception
	def __init__(self, code, http_status, message):
		## Error code of the exception.
		self.code = code
		## A HTTP status code.
		self.http_status = http_status
		## String describing the exception.
		self.message = message

## Exception used for internal failures.
class InternalFailureException(BaseException):
	## The constructor.
	#  @param message message describing the exception
	def __init__(self, message):
		BaseException.__init__(self, ErrorCode.INTERNAL_FAILURE, 500, message)

## Exception raised when a stream exceeds the allowed maximum length.
class StreamExceedsMaximumException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.STREAM_EXCEEDS_MAXIMUM, 413, "The stream exceeds the allowed maximum length.")

## Exception raised when the format of an image is invalid.
class InvalidImageFormatException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.INVALID_IMAGE_FORMAT, 415, "The image has an invalid format.")

## Exception used when a controller doesn't support a method.
class MethodNotSupportedException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.METHOD_NOT_SUPPORTED, 405, "Method not supported.")

## Exception raised when authentication fails.
class AuthenticationFailedException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.AUTHENTICATION_FAILED, 401, "Authentication failed.")

## Exception raised when a user is not authorized.
class NotAuthorizedException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.NOT_AUTHORIZED, 403, "User not authorized.")

## Exception raised when at least one parameter is missing.
class MissingParameterException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.MISSING_PARAMETER, 400, "Missing parameter(s).")

## Exception raised when a specified parameter is invalid.
class InvalidParameterException(BaseException):
	## The constructor.
	#  @param parameter name of the invalid parameter
	def __init__(self, parameter):
		BaseException.__init__(self, ErrorCode.INVALID_PARAMETER, 422, "Invalid parameter: \"%s\"" % (parameter))
		## name of the invalid parameter
		self.parameter = parameter

## Exception raised when a resource cannot be found.
class NotFoundException(BaseException):
	def __init__(self, message):
		BaseException.__init__(self, ErrorCode.NOT_FOUND, 404, message)

## Exception raised when there's a conflict (e.g. an already existing Guid).
class ConflictException(BaseException):
	def __init__(self, message):
		BaseException.__init__(self, ErrorCode.CONFLICT, 409, message)

## Exception raised when a request code is invalid.
class InvalidRequestCodeException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.INVALID_REQUEST_CODE, 422, "Invalid request code.")

## Exception raised when a specified user cannot be found.
class UserNotFoundException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.USER_NOT_FOUND, 404, "Username not found.")

## Exception raised when a user is blocked.
class UserIsBlockedException(BaseException):
	def __init__(self, message="User is blocked."):
		BaseException.__init__(self, ErrorCode.USER_IS_BLOCKED, 423, message)

## Exception raised when a password is wrong.
class WrongPasswordException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.WRONG_PASSWORD, 422, "Wrong password.")

## Exception raised when a mail address is wrong (does not belong to a user account).
class WrongEmailAddressException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.WRONG_EMAIL_ADDRESS, 422, "Wrong email address.")

## Exception raised when a friendship is required but does not exist.
class NoFriendshipExpception(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.NO_FRIENDSHIP, 403, "No friendship.")

## Exception raised when an object cannot be found.
class ObjectNotFoundException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.OBJECT_NOT_FOUND, 404, "Object not found.")

## Exception raised when an object cannot be modified because it's locked.
class ObjectIsLockedException(BaseException):
	def __init__(self):
		BaseException.__init__(self, ErrorCode.OBJECT_IS_LOCKED, 423, "The given object is locked.")

## Exception used for general HTTP expceptions.
class HTTPException(BaseException):
	## The constructor.
	#  @param message message describing the exception
	def __init__(self, http_status, message):
		BaseException.__init__(self, ErrorCode.HTTP_FAILURE, http_status, message)
