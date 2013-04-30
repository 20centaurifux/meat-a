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

import factory, exception, util, config, tempfile, os
from validators import *
from base64 import b64encode
from database import StreamDb

class Application:
	def __init__(self):
		self.__userdb = None
		self.__objectdb = None
		self.__streamdb = None
		self.__shared_client = None

	def __del__(self):
		if not self.__userdb is None:
			self.__userdb = None

		if not self.__objectdb is None:
			self.__objectdb = None

		if not self.__streamdb is None:
			self.__streamdb = None

		if not self.__shared_client is None:
			self.__shared_client.disconnect()

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

	def disable_user(self, username):
		self.__test_active_user__(username)
		self.__create_user_db__().block_user(username)

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

	def get_password(self, username):
		user = self.get_active_user(username)

		return user["password"]

	def request_password(self, username, email, request_timeout = config.PASSWORD_REQUEST_TIMEOUT):
		user = self.get_active_user(username)

		if user["email"] != email:
			raise exception.InvalidEmailAddressException()

		db = self.__create_user_db__()

		# create code:
		code = b64encode(util.generate_junk(config.REQUEST_CODE_LENGTH))

		while db.password_request_code_exists(code):
			code = b64encode(util.generate_junk(config.REQUEST_CODE_LENGTH))

		# save password request:
		db.create_password_request(username, code, request_timeout)

		return code

	def generate_password(self, code):
		db = self.__create_user_db__()

		username = db.get_password_request(code)

		if username is None:
			raise exception.InvalidRequestCodeException()

		user = self.get_active_user(username)

		password = util.generate_junk(config.DEFAULT_PASSWORD_LENGTH)
		db.update_user_password(username, util.hash(password))

		return username, user["email"], password

	def update_user_details(self, username, email, firstname, lastname, gender, language, protected):
		# validate parameters:
		if not validate_email(email):
			raise exception.InvalidParameterException("email")

		if not validate_firstname(firstname):
			raise exception.InvalidParameterException("firstname")

		if not validate_lastname(lastname):
			raise exception.InvalidParameterException("lastname")

		if not validate_gender(gender):
			raise exception.InvalidParameterException("gender")

		if not validate_language(language):
			raise exception.InvalidParameterException("language")

		if protected is None or (protected != True and protected != False):
			raise exception.InvalidParameterException("protected")

		# test if email address is already assigned:
		db = self.__create_user_db__()

		self.__test_active_user__(username)

		user = db.get_user_by_email(email)

		if not user is None and user["name"] != username:
			raise exception.EmailAlreadyAssignedException()

		# update user details:
		db.update_user_details(username, email, firstname, lastname, gender, language, protected)

	def update_avatar(self, username, filename, stream):
		# get file extension:
		ext = os.path.splitext(filename)[1]

		if not ext.lower() in config.AVATAR_EXTENSIONS:
			raise exception.InvalidImageFormatException()

		# test if user is valid:
		self.__test_active_user__(username)

		# write temporary file:
		with tempfile.NamedTemporaryFile(mode = "wb", dir = config.TMP_DIR, delete = False) as f:
			for bytes in util.read_from_stream(stream, max_size = config.AVATAR_MAX_FILESIZE):
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
		db.update_avatar(username, filename)


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

	def get_user_details(self, account, username):
		user_a = self.get_active_user(account)

		if account == username:
			del user_a["blocked"]

			return user_a

		user_b = self.get_active_user(username)

		if (user_b["protected"] and account in user_b["following"] and username in user_a["following"]) or not user_b["protected"]:
			keys = [ "password", "blocked", "language" ]
		else:
			keys = [ "password", "blocked", "email", "following", "language" ]

		for key in keys:
			del user_b[key]

		return user_b

	def find_user(self, account, query):
		user_a = self.get_active_user(account)
		result = []

		for user_b in self.__create_user_db__().search_user(query):
			if user_b["name"] != account:
				if (user_b["protected"] and account in user_b["following"] and user_b["name"] in user_a["following"]) or not user_b["protected"]:
					result.append(user_b)
				else:
					del user_b["email"]
					del user_b["following"]

					result.append(user_b)

		return result

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

	def add_tags(self, username, guid, tags):
		for tag in tags:
			if not validate_tag(tag):
				raise exception.InvalidParameterException("tag")

		self.__test_active_user__(username)
		self.__test_object_write_access__(guid)

		return self.__create_object_db__().add_tags(guid, tags)

	def rate(self, username, guid, up = True):
		self.__test_object_write_access__(guid)
		user = self.get_active_user(username)

		# rate:
		db = self.__create_object_db__()

		if not db.user_can_rate(guid, username):
			raise exception.UserAlreadyRatedException()

		db.rate(guid, username, up)

		# send messages:
		if len(user["following"]) > 0:
			streamdb = self.__create_stream_db__()

			for friend in self.__get_friends__(user):
				streamdb.add_message(StreamDb.MessageType.VOTE, username, friend, guid = guid, up = up)

	def favor(self, username, guid, favor = True):
		self.__test_object_exists__(guid)
		user = self.get_active_user(username)

		# create favorite:
		db = self.__create_object_db__()
		db.favor_object(guid, username, favor)

		# create messages:
		if favor and len(user["following"]) > 0:
			streamdb = self.__create_stream_db__()

			for friend in self.__get_friends__(user):
				streamdb.add_message(StreamDb.MessageType.FAVOR, username, friend, guid = guid)

	def get_favorites(self, username, page = 0, page_size = 10):
		self.__test_active_user__(username)

		return self.__create_object_db__().get_favorites(username, page, page_size)

	def add_comment(self, guid, username, text):
		if not validate_comment(text):
			raise exception.InvalidParameterException("comment")

		self.__test_object_write_access__(guid)
		user = self.get_active_user(username)

		# create comment:
		db = self.__create_object_db__()
		db.add_comment(guid, username, text)

		# send messages:
		if len(user["following"]) > 0:
			streamdb = self.__create_stream_db__()

			for friend in self.__get_friends__(user):
				streamdb.add_message(StreamDb.MessageType.COMMENT, username, friend, guid = guid, comment = text)

	def get_comments(self, guid, page = 0, page_size = 10):
		self.__test_object_exists__(guid)

		return self.__create_object_db__().get_comments(guid, page, page_size)

	def recommend(self, username, guid, receivers):
		sender = self.get_active_user(username)
		self.__test_object_exists__(guid)

		# build valid receiver list:
		valid_receivers = []

		userdb = self.__create_user_db__()
		objdb = self.__create_object_db__()

		for r in receivers:
			if r != username and r in sender["following"]:
				try:
					user = self.get_active_user(r)

					if username in user["following"] and not objdb.recommendation_exists(guid, r):
						valid_receivers.append(r)

				except exception.UserNotFoundException:
					pass

				except exception.UserIsBlockedException:
					pass

		# create recommendations:
		objdb.recommend(guid, username, valid_receivers)

		# send messages:
		streamdb = self.__create_stream_db__()

		for r in valid_receivers:
			streamdb.add_message(StreamDb.MessageType.RECOMMENDATION, username, r, guid = guid)

	def get_recommendations(self, username, page = 0, page_size = 10):
		self.__test_active_user__(username)

		return self.__create_object_db__().get_recommendations(username, page, page_size)

	def follow(self, user1, user2, follow = True):
		self.__test_active_user__(user1)
		self.__test_active_user__(user2)

		# create/destroy friendship:
		self.__create_user_db__().follow(user1, user2, follow)

		# send messages:
		if follow:
			type_id = StreamDb.MessageType.FOLLOW
		else:
			type_id = StreamDb.MessageType.UNFOLLOW

		self.__create_stream_db__().add_message(type_id, user1, user2)

	def is_following(self, user1, user2):
		return self.__create_user_db__().is_following(user1, user2)

	def get_messages(self, username, limit = 100, older_than = None):
		self.__test_active_user__(username)

		return self.__create_stream_db__().get_messages(username, limit, older_than)

	def get_active_user(self, username):
		db = self.__create_user_db__()

		user = db.get_user(username)

		if user is None:
			raise exception.UserNotFoundException()

		if user["blocked"]:
			raise exception.UserIsBlockedException()

		return user

	def __create_shared_client__(self):
		if self.__shared_client is None:
			self.__shared_client = factory.create_shared_client()

		return self.__shared_client

	def __create_user_db__(self):
		if self.__userdb is None:
			self.__userdb = factory.create_shared_user_db(self.__create_shared_client__())

		return self.__userdb

	def __create_object_db__(self):
		if self.__objectdb is None:
			self.__objectdb = factory.create_shared_object_db(self.__create_shared_client__())

		return self.__objectdb

	def __create_stream_db__(self):
		if self.__streamdb is None:
			self.__streamdb = factory.create_shared_stream_db(self.__create_shared_client__())

		return self.__streamdb

	def __test_active_user__(self, username):
		db = self.__create_user_db__()

		if not db.user_exists(username):
			raise exception.UserNotFoundException()

		if db.user_is_blocked(username):
			raise exception.UserIsBlockedException()

	def __test_object_exists__(self, guid):
		db = self.__create_object_db__()

		if not db.object_exists(guid):
			raise exception.ObjectNotFoundException()

	def __test_object_write_access__(self, guid):
		db = self.__create_object_db__()

		if not db.object_exists(guid):
			raise exception.ObjectNotFoundException()

		if db.is_locked(guid):
			raise exception.ObjectIsLockedException()

	def __get_friends__(self, user):
		friends = []

		for u in user["following"]:
			try:
				details = self.get_active_user(u)
				
				if user["name"] in details["following"]:
					friends.append(details["name"])

			except exception.UserIsBlockedException:
				pass

		return friends

class RequestData:
	def __init__(self, username, timestamp = None, signature = None):
		self.username = username

		if timestamp is None:
			self.timestamp = util.unix_timestamp()
		else:
			self.timestamp = timestamp

		self.signature = signature

class AuthenticatedApplication:
	def __init__(self):
		self.__app = None

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if not self.__app is None:
			del self.__app

	def request_account(self, username, email, user_request_timeout = config.USER_REQUEST_TIMEOUT):
		return self.__create_app__().request_account(username, email, user_request_timeout)

	def request_password(self, username, email):
		return self.__create_app__().request_password(username, email)

	def generate_password(self, code):
		return self.__create_app__().generate_password(code)

	def activate_user(self, code):
		return self.__create_app__().activate_user(code)

	def disable_user(self, req, email):
		self.__verify_message__(req, email = email)

		app = self.__create_app__()
		user = app.get_active_user(req.username)

		if user["email"] != email:
			raise exception.InvalidEmailAddressException()

		app.disable_user(req.username)

	def change_password(self, req, old_password, new_password):
		self.__verify_message__(req, old_password = old_password, new_password = new_password)
		self.__create_app__().change_password(req.username, old_password, new_password)

	def update_user_details(self, req, email, firstname, lastname, gender, language, protected):
		self.__verify_message__(req, email = email, firstname = firstname, lastname = lastname, gender = gender, language = language, protected = protected)
		self.__create_app__().update_user_details(req.username, email, firstname, lastname, gender, language, protected)

	def update_avatar(self, req, filename, stream):
		self.__verify_message__(req, filename = filename)
		self.__create_app__().update_avatar(req.username, filename, stream)

	def find_user(self, req, query):
		self.__verify_message__(req, query = query)

		return self.__create_app__().find_user(req.username, query)

	def get_user_details(self, req, name):
		self.__verify_message__(req, name = name)

		return self.__create_app__().get_user_details(req.username, name)

	def get_object(self, req, guid):
		self.__verify_message__(req, guid = guid)

		return self.__create_app__().get_object(guid)

	def get_objects(self, req, page, page_size):
		self.__verify_message__(req, page = page, page_size = page_size)

		return self.__create_app__().get_objects(page, page_size)

	def get_tagged_objects(self, req, tag, page, page_size):
		self.__verify_message__(req, tag = tag, page = page, page_size = page_size)
		return self.__create_app__().get_tagged_objects(tag, page, page_size)

	def get_popular_objects(self, req, page, page_size):
		self.__verify_message__(req, page = page, page_size = page_size)

		return self.__create_app__().get_popular_objects(page, page_size)

	def get_random_objects(self, req, page_size):
		self.__verify_message__(req, page_size = page_size)

		return self.__create_app__().get_random_objects(page_size)

	def add_tags(self, req, guid, tags):
		self.__verify_message__(req, guid = guid, tags = tags)
		self.__create_app__().add_tags(req.username, guid, tags)

	def rate(self, req, guid, up = True):
		self.__verify_message__(req, guid = guid, up = up)
		self.__create_app__().rate(req.username, guid, up)

	def favor(self, req, guid, favor = True):
		self.__verify_message__(req, guid = guid, favor = favor)
		self.__create_app__().favor(req.username, guid, favor = favor)

	def get_favorites(self, req, page, page_size):
		self.__verify_message__(req, page = page, page_size = page_size)

		return self.__create_app__().get_favorites(req.username, page, page_size)

	def add_comment(self, req, guid, text):
		self.__verify_message__(req, guid = guid, text = text)
		self.__create_app__().add_comment(guid, req.username, text)

	def get_comments(self, req, guid, page, page_size):
		self.__verify_message__(req, guid = guid, page = page, page_size = page_size)

		return self.__create_app__().get_comments(guid, page, page_size)

	def recommend(self, req, guid, receivers):
		self.__verify_message__(req, guid = guid, receivers = receivers)
		self.__create_app__().recommend(req.username, guid, receivers)

	def get_recommendations(self, req, page, page_size):
		self.__verify_message__(req, page = page, page_size = page_size)

		return self.__create_app__().get_recommendations(req.username, page, page_size)

	def follow(self, req, user, follow):
		self.__verify_message__(req, user = user, follow = follow)
		self.__create_app__().follow(req.username, user, follow)

	def get_messages(self, req, limit, older_than):
		self.__verify_message__(req, limit = limit, older_than = older_than)

		return self.__create_app__().get_messages(req.username, limit, older_than)

	def __verify_message__(self, req, **kwargs):
		try:
			# validate timestamp:
			if util.unix_timestamp() - req.timestamp > config.REQUEST_EXPIRY_TIME:
				raise exception.RequestExpiredException

			# get user password:
			password = self.__get_user_password__(req.username)

			if password is None:
				raise exception.AuthenticationFailedException()

			# verify signature:
			kwargs["username"] = req.username
			kwargs["timestamp"] = req.timestamp

			signature = util.sign_message(str(password), **kwargs)

			if signature != req.signature:
				raise exception.AuthenticationFailedException()

		except exception.AuthenticationFailedException, ex:
			raise ex

		except exception.RequestExpiredException, ex:
			raise ex

		except Exception:
			raise exception.InvalidRequestException()

	def __get_user_password__(self, username):
		return self.__create_app__().get_password(username)
		
	def __create_app__(self):
		if self.__app is None:
			self.__app = Application()

		return self.__app
