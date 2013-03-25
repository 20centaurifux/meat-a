import util

ErrorCode = util.enum(INVALID_PARAMETER = 1,
                      USER_ALREADY_EXISTS = 100,
                      USERNAME_ALREADY_REQUESTED = 101,
                      EMAIL_ALREADY_ASSIGNED = 102,
                      INVALID_REQUEST_CODE = 103)

class Exception:
	def __init__(self, code, message):
		self.code = code
		self.message = message

class InvalidParameterException(Exception):
	def __init__(self, parameter):
		Exception.__init__(self, ErrorCode.INVALID_PARAMETER, "Invalid parameter.")
		self.parameter = parameter

class UserAlreadyExistsException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USER_ALREADY_EXISTS, "The given username does already exist.")


class UsernameAlreadyRequestedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.USERNAME_ALREADY_REQUESTED, "The given username has already been requested.")

class EmailAlreadyAssignedException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.EMAIL_ALREADY_ASSIGNED, "The given email address is already in use.")

class InvalidRequestCodeException(Exception):
	def __init__(self):
		Exception.__init__(self, ErrorCode.INVALID_REQUEST_CODE, "Invalid request code.")
