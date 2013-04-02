# -*- coding: utf-8 -*-

import factory, exception, util, config, tempfile, os
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
				raise ex

			finally:
				db.close()

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
			db.create_user(request["name"], request["email"], util.hash(password))

			# remove request code:
			db.remove_user_request(code)

		except exception.Exception, ex:
			raise ex
	
		finally:
			db.close()

		return request["name"], request["email"], password

	def change_password(self, username, old_password, new_password):
		if not validate_password(new_password):
			raise exception.InvalidParameterException("new_password")

		db = factory.create_user_db()

		try:
			self.__test_active_user__(db, username)

			password = db.get_user_password(username)
			hash = util.hash(old_password)

			if password != hash:
				raise exception.InvalidPasswordException()

			db.update_user_password(username, util.hash(new_password))

		except exception.Exception, ex:
			raise ex

		finally:
			db.close()

	def validate_password(self, username, password):
		db = factory.create_user_db()
		result = False

		try:
			self.__test_active_user__(db, username)
			result = util.hash(password) == db.get_user_password(username)

		except exception.Exception, ex:
			raise ex

		finally:
			db.close()

		return result

	def update_user_details(self, username, email, firstname, lastname, gender):
		# validate parameters:
		if not validate_email(email):
			raise exception.InvalidParameterException("email")

		if not validate_firstname(firstname):
			raise exception.InvalidParameterException("firstname")

		if not validate_lastname(lastname):
			raise exception.InvalidParameterException("lastname")

		if not validate_gender(gender):
			raise exception.InvalidParameterException("gender")

		# test if email address is already assigned:
		db = factory.create_user_db()

		try:
			self.__test_active_user__(db, username)

			user = db.get_user_by_email(email)

			if not user is None and user["name"] != username:
				raise exception.EmailAlreadyAssignedException()

			# update user details:
			db.update_user_details(username, email, firstname, lastname, gender)

		except exception.Exception, ex:
			raise ex

		finally:
			db.close()

	def update_avatar(self, username, filename, stream):
		# get file extension:
		ext = os.path.splitext(filename)[1]

		if len(ext) == 0:
			raise exception.InvalidImageFormatException()

		# test if user is valid:
		db = factory.create_user_db()

		try:
			self.__test_active_user__(db, username)

		except exception.Exception, ex:
			db.close()
			raise ex

		# write temporary file:
		f = tempfile.NamedTemporaryFile(mode = "wb", dir = config.TMP_DIR, delete = False)

		for bytes in util.read_from_stream(stream):
			f.write(bytes)

		f.close()

		try:
			# validate image format:
			if not validate_image_file(f.name, config.AVATAR_MAX_FILESIZE, config.AVATAR_MAX_WIDTH, config.AVATAR_MAX_HEIGHT, config.AVATAR_FORMATS):
				raise exception.InvalidImageFormatException()

		except exception.Exception, ex:
			os.unlink(f.name)
			db.close()
			raise ex

		# move file to avatar folder:
		try:
			while True:
				filename = "%s%s" % (util.hash("%s-%s-%s" % (util.now(), username, filename)), ext)
				path = os.path.join(config.AVATAR_DIR, filename)

				if not os.path.exists(path):
					break

			os.rename(f.name, path)

		except EnvironmentError, err:
			os.unlink(f.name)
			db.close()

			raise exception.InternalFailureException(str(err))

		# update database:
		try:
			db.update_avatar(username, os.path.basename(path))

		except exception.Exception, ex:
			raise ex

		finally:
			db.close()

	def get_user_details(self, username):
		db = factory.create_user_db()

		try:
			details = db.get_user(username)

			if details is None:
				raise exception.UserNotFoundException()

			if details["blocked"]:
				raise exception.UserNotFoundException()

			del details["password"]
			del details["blocked"]

			return details

		except exception.Exception, ex:
			raise ex

		finally:
			db.close()

	def find_user(self, query):
		db = factory.create_user_db()

		try:
			result = db.search_user(query)

			return result

		except exception.Exception, ex:
			raise ex

		finally:
			db.close()

	def __test_active_user__(self, db, username):
		if not db.user_exists(username):
			raise exception.UserNotFoundException()

		if db.user_is_blocked(username):
			raise exception.UserIsBlockedException()
