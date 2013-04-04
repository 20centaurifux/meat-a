# -*- coding: utf-8 -*-

import factory, exception, util, config, tempfile, os
from validators import *
from base64 import b64encode

class Application:
	def __init__(self):
		self.__userdb = None
		self.__objectdb = None

	def __del__(self):
		if not self.__userdb is None:
			self.__userdb.close()
			self.__userdb = None

		if not self.__objectdb is None:
			self.__objectdb.close()
			self.__objectdb = None

	def __enter__(self):
		return Application()

	def __exit__(self, type, value, traceback):
		self.__del__()
		
	def request_account(self, username, email, user_request_timeout = config.USER_REQUEST_TIMEOUT):
		# validate parameters:
		if not validate_username(username):
			raise exception.InvalidParameterException("username")

		if not validate_email(email):
			raise exception.InvalidParameterException("email")

		# connect to database:
		db = self.__create_user_db__()

		# test if user request, account or email already exist:
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

		return code

	def activate_user(self, code):
		# connect to database:
		db = self.__create_user_db__()

		# find request code:
		request = db.get_user_request(code)

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

		return request["name"], request["email"], password

	def change_password(self, username, old_password, new_password):
		if not validate_password(new_password):
			raise exception.InvalidParameterException("new_password")

		db = self.__create_user_db__()

		self.__test_active_user__(username)

		password = db.get_user_password(username)
		hash = util.hash(old_password)

		if password != hash:
			raise exception.InvalidPasswordException()

		db.update_user_password(username, util.hash(new_password))

	def validate_password(self, username, password):
		db = self.__create_user_db__()

		self.__test_active_user__(username)

		return util.hash(password) == db.get_user_password(username)

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
		db = self.__create_user_db__()

		self.__test_active_user__(username)

		user = db.get_user_by_email(email)

		if not user is None and user["name"] != username:
			raise exception.EmailAlreadyAssignedException()

		# update user details:
		db.update_user_details(username, email, firstname, lastname, gender)

	def update_avatar(self, username, filename, stream):
		# get file extension:
		ext = os.path.splitext(filename)[1]

		if len(ext) == 0:
			raise exception.InvalidImageFormatException()

		# test if user is valid:
		self.__test_active_user__(username)

		# write temporary file:
		with tempfile.NamedTemporaryFile(mode = "wb", dir = config.TMP_DIR, delete = False) as f:
			for bytes in util.read_from_stream(stream):
				f.write(bytes)

		# validate image format:
		try:
			if not validate_image_file(f.name, config.AVATAR_MAX_FILESIZE, config.AVATAR_MAX_WIDTH, config.AVATAR_MAX_HEIGHT, config.AVATAR_FORMATS):
				raise exception.InvalidImageFormatException()

		except exception.Exception, ex:
			os.unlink(f.name)
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
			raise exception.InternalFailureException(str(err))

		# update database:
		db = self.__create_user_db__()
		db.update_avatar(username, os.path.basename(path))

	def get_full_user_details(self, username):
		db = self.__create_user_db__()
		details = db.get_user(username)

		if details is None:
			raise exception.UserNotFoundException()

		if details["blocked"]:
			raise exception.UserNotFoundException()

		del details["password"]
		del details["blocked"]

		return details

	def get_user_details(self, username):
		details = self.get_full_user_details(username)
		del details["email"]

		return details

	def find_user(self, query):
		db = self.__create_user_db__()

		return db.search_user(query)

	def get_object(self, guid):
		return self.__create_object_db__().get_object(guid)

	def get_objects(self, page = 0, page_size = 10):
		return self.__create_object_db__().get_objects(page, page_size)

	def get_tagged_objects(self, tag, page = 0, page_size = 10):
		return self.__create_object_db__().get_tagged_objects(tag, page, page_size)
		
	def get_popular_objects(self, page = 0, page_size = 10):
		return self.__create_object_db__().get_popular_objects(page, page_size)

	def get_random_objects(self, page_size = 10):
		return self.__create_object_db__().get_random_objects(page_size)

	def add_tags(self, guid, tags):
		self.__test_object_write_access__(guid)

		return self.__create_object_db__().add_tags(guid, tags)

	def rate(self, username, guid, up = True):
		self.__test_active_user__(username)
		self.__test_object_write_access__(guid)

		db = self.__create_object_db__()

		if not db.user_can_rate(guid, username):
			raise exception.UserAlreadyRatedException()

		db.rate(guid, username, up)

	def __create_user_db__(self):
		if self.__userdb is None:
			self.__userdb = factory.create_user_db()

		return self.__userdb

	def __create_object_db__(self):
		if self.__objectdb is None:
			self.__objectdb = factory.create_object_db()

		return self.__objectdb

	def __test_active_user__(self, username):
		db = self.__create_user_db__()

		if not db.user_exists(username):
			raise exception.UserNotFoundException()

		if db.user_is_blocked(username):
			raise exception.UserIsBlockedException()

	def __test_object_write_access__(self, guid):
		db = self.__create_object_db__()

		if not db.object_exists(guid):
			raise exception.ObjectNotFoundException()

		if db.is_locked(guid):
			raise exception.ObjectIsLockedException()
