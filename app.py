import factory, exception, util, config
from validators import *
from base64 import b64encode

class Application:
	def request_account(self, username, email):
		# validate parameters:
		if not validate_username(username):
			raise exception.InvalidParameterException("username")

		if not validate_email(email):
			raise exception.InvalidParameterException("email")

		# connect to database:
		db = factory.create_user_db()

		# test if user request, account or email already exist:
		if db.username_requested(username):
			raise exception.UsernameAlreadyRequestedException()

		if db.user_exists(username):
			raise exception.UserAlreadyExistsException()

		if db.email_assigned(email):
			raise exception.EmailAlreadyAssignedException()

		# create activation code:
		code = b64encode(util.generate_junk(128))

		while db.user_request_code_exists(code):
			code = b64encode(util.generate_junk(128))

		# save user request:
		db.create_user_request(username, email, code, config.USER_REQUEST_TIMEOUT)

		return code
