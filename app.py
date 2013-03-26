import factory, exception, util, config
from validators import *
from base64 import b64encode

class Application:
	def request_account(self, username, email, user_request_timeout = config.USER_REQUEST_TIMEOUT):
			# validate parameters:
			if not validate_username(username):
				raise exception.InvalidParameterException("username")

			if not validate_email(email):
				raise exception.InvalidParameterException("email")

			# connect to database:
			db = factory.create_user_db()

			# test if user request, account or email already exist:
			try:
				if db.username_requested(username):
					raise exception.UsernameAlreadyRequestedException()

				if db.user_exists(username):
					raise exception.UserAlreadyExistsException()

				if db.email_assigned(email):
					raise exception.EmailAlreadyAssignedException()

				# create activation code:
				code = b64encode(util.generate_junk(config.REQUEST_CODE_LENGTH))

				while db.user_request_code_exists(code):
					code = b64encode(util.generate_junk(config.REQUEST_CODE_LENGTH))

				# save user request:
				db.create_user_request(username, email, code, user_request_timeout)

			except exception.Exception, ex:
				# disconnect from database:
				db.close()

				raise ex

			return code

	def activate_user(self, code):
		# connect to database:
		db = factory.create_user_db()

		try:
			request = db.get_user_request(code)

			# find request code:
			if request is None:
				raise exception.InvalidRequestCodeException()

			# test if username exist or email is already assigned:
			if db.user_exists(request["name"]):
				raise exception.UserAlreadyExistsException()

			if db.email_assigned(request["email"]):
				raise exception.EmailAlreadyAssignedException()

			# create user account:
			password = util.generate_junk(config.DEFAULT_PASSWORD_LENGTH)
			db.create_user(request["name"], request["email"], password)

			# remove request code:
			db.remove_user_request(code)

		except exception.Exception, ex:
			# disconnect from database:
			db.close()

			raise ex
	
		return request["name"], request["email"], password
