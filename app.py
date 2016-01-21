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
#  @file app.py
#  Domain layer.

## @package app
#  Domain layer.

import factory, exception, util, config, tempfile, os, template, mailer
from validators import *
from base64 import b64encode

## Shared user account management methods.
class UserTools:
	def __init__(self, db):
		self.__db = db

	## Tests if a user does exist.
	#  @param scope a transaction scope
	#  @param username user to test
	#  @return True if the account does exist
	def __test_user_exists__(self, scope, username):
		if not self.__db.user_exists(scope, username):
			raise exception.UserNotFoundException()

	## Tests if a user does exist and is active (not blocked).
	#  @param scope a transaction scope
	#  @param username user to test
	#  @return True if the account does exist and isn't blocked
	def __test_active_user__(self, scope, username):
		self.__test_user_exists__(scope, username)

		if self.__db.user_is_blocked(scope, username):
			raise exception.UserIsBlockedException()

	## Gets user details depending on friendship.
	#  @param scope a transaction scope
	#  @param requester name of the account requesting the user profile
	#  @param username name of the account the user profile is requested from
	#  @return a dictionary holding user details: { "id": int, "username": str,
	#          "firstname": str, "lastname": str, "email": str, "gender": str,
	#          "created_on": datetime, "avatar": str, "protected": bool,
	#          "blocked": bool, "following": [str] }; if the account is
	#          protected and the user is not following the requester the
	#          fields "email", "avatar" and "following" aren't available
	def __get_user_details__(self, scope, requester, username):
		self.__test_user_exists__(scope, username)

		lusername = username.lower()
		user = self.__db.get_user(scope, username)

		full_profile = False

		if not user["protected"] or (requester.lower() == lusername) or self.__db.is_following(scope, username, requester):
			keys = ["id", "username", "firstname", "lastname", "email", "gender", "created_on", "avatar", "protected", "blocked"]
			full_profile = True
		else:
			keys = ["id", "username", "firstname", "lastname", "gender", "created_on", "protected", "blocked"]

		details = {}

		for k in keys:
			details[k] = user[k]

		if full_profile:
			details["following"] = self.__db.get_followed_usernames(scope, user["username"])

		return details

	## Gets the user of of a user.
	#  @param scope a transaction scope
	#  @param username user to get the id from
	#  @return an id
	def __map_user_id__(self, scope, user_id):
		return self.__db.map_user_id(scope, user_id)

	## Tests if a password is correct.
	#  @param scope a transaction scope
	#  @param username a user account
	#  @param password (plaintext) to test
	#  @return True if the password is correct
	def __validate_password__(self, scope, username, password):
		current_password, salt = self.__db.get_user_password(scope, username)

		return util.password_hash(password, salt) == current_password

	## Returns the language selected by the user.
	#  @param scope a transaction scope
	#  @param user user details (dictionary)
	#  @return the language selected by the user or config.DEFAULT_LANGUAGE if undefined
	def __get_language__(self, user):
		lang = user["language"]

		if lang is None or len(lang) == 0 or lang not in config.LANGUAGES:
			lang = config.DEFAULT_LANGUAGE

		return lang

## Shared object management methods.
class ObjectTools:
	def __init__(self, db):
		self.__db = db

	## Tests if an object does exist
	#  @param scope a transaction scope
	#  @param guid guid of the object to test
	#  @return True if the object does exist
	def __test_object_exists__(self, scope, guid):
		if not self.__db.object_exists(scope, guid):
			raise exception.ObjectNotFoundException()

	## Tests if an object does exist and isn't locked
	#  @param scope a transaction scope
	#  @param guid guid of the object to test
	#  @return True if the object does exist and isn't locked
	def __test_writeable_object__(self, scope, guid):
		self.__test_object_exists__(scope, guid)

		obj = self.__db.get_object(scope, guid)

		if obj["locked"]:
			raise exception.ObjectIsLockedException()

## A cache for looking up friendship dependend user details.
class UserCache(UserTools):
	def __init__(self, db, requester):
		UserTools.__init__(self, db)

		self.__cache = {}
		self.__requester = requester

	## Gets user details.
	#  @param scope a transaction scope
	#  @param username name of the user profile to get
	#  @return a dictionary holding user details
	def lookup(self, scope, username):
		lusername = username.lower()
		details = None

		try:
			return self.__cache[lusername]

		except KeyError:
			try:
				details = self.__get_user_details__(scope, self.__requester, username)

			except exception.UserNotFoundException:
				details = { "username": username }

		self.__cache[lusername] = details

		return details

	## Gets user details.
	#  @param scope a transaction scope
	#  @param user_id id of the user profile to get
	#  @return a dictionary holding user details
	def lookup_by_id(self, scope, user_id):
		return self.lookup(scope, self.__map_user_id__(scope, user_id))

## The meat-a application layer.
class Application(UserTools, ObjectTools):
	def __init__(self):
		self.__user_db = factory.create_user_db()
		self.__object_db = factory.create_object_db()
		self.__stream_db = factory.create_stream_db()
		self.__mail_db = factory.create_mail_db()

		UserTools.__init__(self, self.__user_db)
		ObjectTools.__init__(self, self.__object_db)

	## Requests a new user account. Username and email have to be unique. On success a
	#  mail is generated and stored in the mail queue.
	#  @param username name of the user to create
	#  @param email email address of the user
	#  @return an auto-generated request id and code needed to activate the account
	def request_account(self, username, email):
		# validate parameters:
		if not validate_username(username):
			raise exception.InvalidParameterException("username")

		if not validate_email(email):
			raise exception.InvalidParameterException("email")

		# store request in database:
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				# test if user account or email already exist:
				if self.__user_db.username_or_email_assigned(scope, username, email):
					raise exception.UsernameOrEmailAlreadyExistException()

				# generate request id & code:
				id = b64encode(util.generate_junk(config.REQUEST_ID_LENGTH))

				while self.__user_db.user_request_id_exists(scope, id):
					id = b64encode(util.generate_junk(config.REQUEST_ID_LENGTH))

				code = b64encode(util.generate_junk(config.REQUEST_CODE_LENGTH))

				# save user request:
				self.__user_db.create_user_request(scope, id, code, username, email)

				# generate mail:
				url = config.USER_ACTIVATION_URL % (id, code)

				tpl = template.AccountRequestMail(config.DEFAULT_LANGUAGE)
				tpl.bind(username=username, url=url)
				subject, body = tpl.render()

				self.__mail_db.push_mail(scope, subject, body, email)

				mailer.ping(config.MAILER_HOST, config.MAILER_PORT)

				scope.complete()

				return id, code

	## Activates a user account. Generates a mail on success.
	#  @param id a request id generated by the Application::request_account() method
	#  @param code a related request code
	#  @return username, email & password (plaintext) of the activated account
	def activate_user(self, id, code):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				# find request id & test code:
				request = self.__user_db.get_user_request(scope, id)

				if request is None:
					raise exception.InvalidRequestIdException()

				if request["request_code"] != code:
					raise exception.InvalidRequestCodeException()

				# activate user account:
				password = util.generate_junk(config.DEFAULT_PASSWORD_LENGTH)
				salt = util.generate_junk(config.PASSWORD_SALT_LENGTH)

				user_id = self.__user_db.activate_user(scope, id, code, util.password_hash(password, salt), salt)

				# generate mail:
				tpl = template.AccountActivatedMail(config.DEFAULT_LANGUAGE)
				tpl.bind(username=request["username"], password=password)
				subject, body = tpl.render()

				self.__mail_db.push_user_mail(scope, subject, body, user_id)

				mailer.ping(config.MAILER_HOST, config.MAILER_PORT)

				scope.complete()

				return request["username"], request["email"], password

	## Disables a user account. Generates a mail on success.
	#  @param username name of the account to disable
	#  @param disabled True to disable the account
	def disable_user(self, username, disabled=True):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_user_exists__(scope, username)

				details = self.__user_db.get_user(scope, username)

				if details["blocked"] and disabled:
					raise exception.UserIsBlockedException()
				elif not details["blocked"] and not disabled:
					raise exception.UserNotBlockedException()

				self.__user_db.block_user(scope, username, disabled)

				tpl = template.AccountDisabledMail(self.__get_language__(details, disabled))
				tpl.bind(username=username)
				subject, body = tpl.render()

				self.__mail_db.push_user_mail(scope, subject, body, details["id"])

				mailer.ping(config.MAILER_HOST, config.MAILER_PORT)

				scope.complete()

	## Deletes a user account. Generates a mail on success.
	#  @param username name of the account to delete
	def delete_user(self, username):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_user_exists__(scope, username)

				details = self.__user_db.get_user(scope, username)

				self.__user_db.delete_user(scope, username, True)

				# generate mail:
				tpl = template.AccountDeletedMail(self.__get_language__(details))
				tpl.bind(username=username)
				subject, body = tpl.render()

				self.__mail_db.push_mail(scope, subject, body, details["email"])

				mailer.ping(config.MAILER_HOST, config.MAILER_PORT)

				scope.complete()

	## Changes the password of a user account. Generates a mail on success.
	#  @param username name of a user account
	#  @param old_password old password (plaintext) of the specified account
	#  @param new_password1 a new password (plaintext) to set
	#  @param new_password2 repeated new password (plaintext)
	def change_password(self, username, old_password, new_password1, new_password2):
		# validate passwords:
		if not validate_password(new_password1):
			raise exception.InvalidParameterException("new_password")

		if new_password1 != new_password2:
			raise exception.PasswordsNotEqualException()

		# change password:
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				if self.__validate_password__(scope, username, old_password):
					# change password:
					salt = util.generate_junk(config.PASSWORD_SALT_LENGTH)
					hash = util.password_hash(new_password1, salt)

					self.__user_db.update_user_password(scope, username, hash, salt)

					# generate mail:
					user = self.__user_db.get_user(scope, username)

					tpl = template.PasswordChangedMail(self.__get_language__(user))
					tpl.bind(username=username)
					subject, body = tpl.render()

					self.__mail_db.push_user_mail(scope, subject, body, user["id"])

					mailer.ping(config.MAILER_HOST, config.MAILER_PORT)

					scope.complete()
				else:
					raise exception.InvalidPasswordException()

	## Tests if a password is correct.
	#  @param username a user account
	#  @param password password (plaintext) to validate
	#  @return True if the given password is correct
	def validate_password(self, username, password):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				return self.__validate_password__(scope, username, password)

	## Generates a password request and email.
	#  @param username a user account
	#  @param email email address of the specified user account
	#  @return an auto-generated id and code to change the user password
	def request_new_password(self, username, email):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				user = self.__user_db.get_user(scope, username)

				# test if email address is correct:
				if email.lower() <> user["email"].lower():
					raise exception.InvalidEmailAddressException()

				# delete existing request ids:
				self.__user_db.remove_password_requests_by_user_id(scope, user["id"])

				# create request id & code:
				id = b64encode(util.generate_junk(config.REQUEST_ID_LENGTH))

				while self.__user_db.password_request_id_exists(scope, id):
					id = b64encode(util.generate_junk(config.REQUEST_ID_LENGTH))

				code = b64encode(util.generate_junk(config.REQUEST_CODE_LENGTH))
				url = config.PASSWORD_RESET_URL % (id, code)

				# save password request:
				self.__user_db.create_password_request(scope, id, code, user["id"])

				# generate mail:
				tpl = template.PasswordRequestedMail(self.__get_language__(user))
				tpl.bind(username=username, url=url)
				subject, body = tpl.render()

				self.__mail_db.push_user_mail(scope, subject, body, user["id"])

				mailer.ping(config.MAILER_HOST, config.MAILER_PORT)

				scope.complete()

				return id, code

	## Resets a password using a generated password request id & code. Generates a mail on success.
	#  @param id a password request id
	#  @param code a related request code
	#  @param new_password1 a new password (plaintext)
	#  @param new_password2 repeated new password (plaintext)
	def reset_password(self, id, code, new_password1, new_password2):
		# validate passwords:
		if not validate_password(new_password1):
			raise exception.InvalidParameterException("new_password")

		if new_password1 != new_password2:
			raise exception.PasswordsNotEqualException()

		# reset password:
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				# find request id & test code:
				request = self.__user_db.get_password_request(scope, id)
				username = request["user"]["username"]

				self.__test_user_exists__(scope, username)

				if request is None:
					raise exception.InvalidRequestIdException()

				if request["request_code"] != code:
					raise exception.InvalidRequestCodeException()

				# change password:
				salt = util.generate_junk(config.PASSWORD_SALT_LENGTH)

				hash = util.password_hash(new_password1, salt)
				self.__user_db.reset_password(scope, id, code, hash, salt)

				# generate mail:
				user = self.__user_db.get_user(scope, username)

				tpl = template.PasswordChangedMail(self.__get_language__(user))
				tpl.bind(username=username)
				subject, body = tpl.render()

				self.__mail_db.push_user_mail(scope, subject, body, user["id"])

				mailer.ping(config.MAILER_HOST, config.MAILER_PORT)

				scope.complete()

	## Updates the details of a user account.
	#  @param username a user account
	#  @param email email address to set
	#  @param firstname firstname to set
	#  @param lastname lastname to set
	#  @param gender gender to set
	#  @param language language to set
	#  @param protected protected status to set
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

		# update user details:
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				# test email
				if not self.__user_db.user_can_change_email(scope, username, email):
					raise exception.EmailAlreadyAssignedException()

				# update user details:
				self.__user_db.update_user_details(scope, username, email, firstname, lastname, gender, language, protected)

				scope.complete()

	## Updates the avatar of a user account.
	#  @param username a user account
	#  @param filename filename of the image
	#  @param stream input stream for reading image data
	def update_avatar(self, username, filename, stream):
		# get file extension:
		ext = os.path.splitext(filename)[1]

		if not ext.lower() in config.AVATAR_EXTENSIONS:
			raise exception.InvalidImageFormatException()

		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				# test if user is active:
				self.__test_active_user__(scope, username)

				# write temporary file:
				with tempfile.NamedTemporaryFile(mode = "wb", dir = config.TMP_DIR, delete = False) as f:
					map(f.write, util.read_from_stream(stream, max_size = config.AVATAR_MAX_FILESIZE))

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
						filename = "%s%s" % (util.hash("%s-%s-%s-%s" % (util.now(), util.generate_junk(32), username, filename)), ext)
						path = os.path.join(config.AVATAR_DIR, filename)

						if not os.path.exists(path):
							break

					os.rename(f.name, path)

					# update database:
					self.__user_db.update_avatar(scope, username, filename)

					scope.complete()

				except EnvironmentError, err:
					os.unlink(f.name)
					raise exception.InternalFailureException(str(err))

	## Gets all details of a user account excepting blocked status and password.
	#  @param username a user account
	#  @return a dictionary holding user information: { "username": str, "firstname": str, "lastname": str, "email": str,
	#          "gender": str, "created_on": datetime, "avatar": str, "protected": bool, "following":  [str],
	#          "blocked": bool, "language": str }
	def get_full_user_details(self, username):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_user_exists__(scope, username)

				details = self.__user_db.get_user(scope, username)

				user = {}

				for k in ["username", "firstname", "lastname", "email", "gender", "created_on", "avatar", "protected", "blocked", "language"]:
					user[k] = details[k]

				user["following"] = db.get_followed_usernames(scope, username)

				return user

	## Gets details of a user account depending on protected status and friendship.
	#  @param account user account who wants to receive the user details
	#  @param username user to get details from
	#  @return a dictionary holding user details: { "id": int, "username": str,
	#          "firstname": str, "lastname": str, "email": str, "gender": str,
	#          "created_on": datetime, "avatar": str, "protected": bool,
	#          "blocked": bool, "following": [str] }; if the account is
	#          protected and the user is not following the requester the
	#          fields "email", "avatar" and "following" aren't available
	def get_user_details(self, account, username):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, account)

				return self.__get_user_details__(scope, user_a, username)

	## Finds users by a search query.
	#  @param account user account who searches the data store
	#  @param query a search query
	#  @return a dictionary holding user details: { "id": int, "username": str,
	#          "firstname": str, "lastname": str, "email": str, "gender": str,
	#          "created_on": datetime, "avatar": str, "protected": bool,
	#          "blocked": bool, "following": [str] }; if the account is
	#          protected and the user is not following the requester the
	#          fields "email", "avatar" and "following" aren't available
	def find_user(self, account, query):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, account)

				# get details from requester:
				requester = self.__user_db.get_user(scope, account)

				# search users:
				lusername = username.lower()
				result = []

				for username in db.search(scope, query):
					if lusername <> requester["username"].lower():
						result.append(self.__get_user_details__(scope, db, requester, username))

				return result

	## Lets one user follow another user. The followed user receives a notification.
	#  @param user1 user who wants to follow another user
	#  @param user2 the user account user1 wants to follow
	#  @param follow True to follow, False to unfollow
	def follow(self, user1, user2, follow=True):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				db = self.__user_db

				if user1 == user2:
					raise InvalidParameterException("user2")

				self.__test_active_user__(scope, user1)
				self.__test_active_user__(scope, user2)

				is_following = db.is_following(scope, user1, user2)

				if follow and is_following:
					raise exception.UserAlreadyFollowingException()
				elif not follow and not is_following:
					raise exception.UserAlreadyFollowingException()

				details1 = db.get_user(scope, user1)
				details2 = db.get_user(scope, user2)

				db.follow(scope, details1["id"], details2["id"], follow)

				scope.complete()

	## Creates a new object.
	#  @param guid guid of the object
	#  @param source object source
	def create_object(self, guid, source):
		# validate parameters:
		if not validate_guid(guid):
			raise exception.InvalidParameterException("guid")

		# create object:
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				db = self.__object_db

				if db.object_exists(scope, guid):
					raise exception.ObjectAlreadyExists()

				db.create_object(scope, guid, source)

				scope.complete()

	## Locks an object.
	#  @param guid guid of the object
	#  @param locked True to lock object
	def lock_object(self, guid, locked):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_object_exists__(scope, guid)
				self.__object_db.lock_object(scope, guid, locked)

				scope.complete()

	## Deleted an object.
	#  @param guid guid of the object
	#  @param deleted True to delete object
	def delete_object(self, guid, deleted):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_object_exists__(scope, guid)
				self.__object_db.delete_object(scope, guid, deleted)

				scope.complete()

	## Gets object details.
	#  @param guid an object guid
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_object(self, guid):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_object_exists__(scope, guid)

				return self.__object_db.get_object(scope, guid)

	## Gets objects from the data store.
	#  @param page page number
	#  @param page_size size of each page
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_objects(self, page = 0, page_size = 10):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				return self.__object_db.get_objects(scope, page, page_size)

	## Gets the most popular objects.
	#  @param page page number
	#  @param page_size size of each page
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_popular_objects(self, page = 0, page_size = 10):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				return self.__object_db.get_popular_objects(scope, page, page_size)

	## Gets objects assigned to a tag.
	#  @param tag tag to search
	#  @param page page number
	#  @param page_size size of each page
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_tagged_objects(self, tag, page = 0, page_size = 10):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				return self.__object_db.get_tagged_objects(scope, tag, page, page_size)

	## Gets random objects.
	#  @param page_size number of objects the method should(!) return
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_random_objects(self, page_size=10):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				return self.__object_db.get_random_objects(scope, page_size)

	## Adds tags to an object.
	#  @param guid guid of an object
	#  @param username user who wants to add tags
	#  @param tags array containing tags to add
	def add_tags(self, guid, username, tags):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)
				self.__test_writeable_object__(scope, guid)

				user = self.__user_db.get_user(scope, username)

				for tag in tags:
					self.__object_db.add_tag(scope, guid, user["id"], tag)

				scope.complete()

	## Gets a tag cloud.
	#  @return an array holding tag details: [ { "tag": str, "count": int }, ... ]
	def get_tag_cloud(self):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				return self.__object_db.get_tags(scope)

	## Upvotes/Downvotes an object.
	#  @param username user who wants to vote
	#  @param guid guid of an object
	#  @param up True to upvote
	def vote(self, username, guid, up=True):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope,  username)
				self.__test_writeable_object__(scope, guid)

				if not self.__object_db.user_can_vote(scope, guid, username):
					raise exception.UserAlreadyRatedException()

				user = self.__user_db.get_user(scope, username)

				self.__object_db.vote(scope, guid, user["id"], up)

				scope.complete()

	## Adds an object to the favorites list of a user. Friends & unprotected followed users receive a notification.
	#  @param username user who wants to add the object to his/her favorites list
	#  @param guid guid of an object
	#  @param favor True to add the object to the list
	def favor(self, username, guid, favor=True):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)
				self.__test_object_exists__(scope, guid)

				user = self.__user_db.get_user(scope, username)
				is_favorite = self.__user_db.is_favorite(scope, user["id"], guid)

				if favor and is_favorite:
					raise exception.FavoriteAlreadyExistException()
				elif not favor and not is_favorite:
					raise exception.FavoriteNotFoundException()

				self.__user_db.favor(scope, user["id"], guid, favor)

				scope.complete()

	## Returns the favorites list of a user.
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_favorites(self, username, page = 0, page_size = 10):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				user = self.__user_db.get_user(scope, username)

				return self.__user_db.get_favorites(scope, user["id"])

	## Appends a comment to an object. Friends & unprotected followed users receive a notification.
	#  @param guid guid of an object
	#  @param username author of the comment
	#  @param text text to append
	def add_comment(self, guid, username, text):
		if not validate_comment(text):
			raise exception.InvalidParameterException("comment")

		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)
				self.__test_writeable_object__(scope, guid)

				user = self.__user_db.get_user(scope, username)
				self.__object_db.add_comment(scope, guid, user["id"], text)

				scope.complete()

	## Gets comments assigned to an object.
	#  @param username user who wants to receive the comments
	#  @param guid guid of an object
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding a comment, the received user details of the author
	#          depend on the friendship status: [ { "text": str, "timestamp": datetime, "deleted": bool,
	#          "user": { } } ]
	def get_comments(self, username, guid, page=0, page_size=100):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(username)
				self.__test_object_exists__(scope, guid)

				user = self.__user_db.get_user(scope, username)
				comments = self.__object_db.get_comments(scope, guid, page, page_size)
				cache = UserCache(self.__user_db, username)

				for comment in comments:
					self.__prepare_comment__(scope, comment, cache)

				return comments

	## Lets a user recommend an object to his/her friends or followed unprotected users.
	#  Each receiver gets a notification.
	#  @param username user who wants to recommend an object
	#  @param guid guid of an object
	#  @param receivers array containing receiver names
	def recommend(self, username, receivers, guid):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)
				self.__test_object_exists__(scope, guid)

				sender = self.__user_db.get_user(scope, username)

				receiver_set = set()
				lsender = username.lower()

				for r in receivers:
					lname = r.lower()

					if lname in receiver_set or lname == lsender:
						continue

					self.__test_active_user__(scope, name)
					details = self.__user_db.get_user(scope, name)

					if details["protected"] and not self.__user_db.is_following(scope, name, username):
						raise exception.UserNotFollowingException()

					if not self.__user_db.recommendation_exists(scope, username, r, guid):
						self.__user_db.recommend(scope, sender["id"], details["id"], guid)

					receiver_set.add(name)

				scope.complete()


	## Gets objects recommended to a user.
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	def get_recommendations(self, username, page=0, page_size=10):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				cache = UserCache(self.__user_db, username)
				recommendations = self.__user_db.get_recommendations(scope, username, page, page_size)

				for r in recommendations:
					r["from"] = cache.lookup(scope, username)
					del r["username"]

					r["object"] = self.get_object(r["guid"])
					del r["guid"]

				return recommendations

	## Reports an object for abuse.
	#  @param guid guid of an object
	#  @return True if the object has been reported
	def report_abuse(self, guid):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_object_exists__(guid)
				self.__object_db.report_abuse(scope, guid)

	## Gets messages sent to a user account.
	#  @param username a user account
	#  @param limit number of messages to receive
	#  @param older_than filter to get only messages older than the specified timestamp
	#  @return an array, each element is a dictionary holding a message ({ "type_id": int, "timestamp": float,
	#          "sender": { "name": str, "firstname": str, "lastname": str, "gender": str, "avatar": str, "blocked": bool },
	#          [ optional fields depending on message type] })
	def get_messages(self, username, limit=100, older_than=None):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(username)
				messages = []
				cache = UserCache(self.__user_db, username)

				for msg in self.__stream_db.get_messages(scope, username, limit, older_than):
					messages.append(self.__build_message__(scope, username, cache, msg))

				return messages

	## Gets public messages.
	#  @param username a user account
	#  @param limit number of messages to receive
	#  @param older_than filter to get only messages older than the specified timestamp
	#  @return an array, each element is a dictionary holding a message ({ "type_id": int, "timestamp": float,
	#          "sender": { "name": str, "firstname": str, "lastname": str, "gender": str, "avatar": str, "blocked": bool },
	#          [ optional fields depending on message type] })
	def get_public_messages(self, username, limit=100, older_than=None):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				messages = []
				cache = UserCache(self.__user_db, username)

				for msg in self.__stream_db.get_public_messages(scope, limit, older_than):
					messages.append(self.__build_message__(scope, username, cache, msg))

				return messages

	def __build_message__(self, scope, username, cache, m):
		msg = {}

		for k in ["id", "created_on", "type"]:
			msg[k] = m[k]

		source = cache.lookup_by_id(scope, m["source"])
		msg["source"] = source

		if m["type"] == "recommendation":
			guid = m["target"]
			self.__test_object_exists__(scope, guid)

			msg["target"] = self.__object_db.get_object(scope, guid)

		elif m["type"] == "wrote-comment":
			id = m["target"]

			if not self.__object_db.comment_exists(scope, id):
				raise exception.CommentNotFoundException()

			comment = self.__object_db.get_comment(scope, id)
			self.__prepare_comment__(scope, comment, cache)

			msg["target"] = comment

		elif m["type"] == "voted-object":
			msg["vote"] = self.__object_db.get_vote(scope, m["target"], source["username"])

		return msg

	def __prepare_comment__(self, scope, comment, cache):
		# set author's user details:
		comment["user"] = cache.lookup(scope, comment["username"])
		del comment["username"]

		# remove text if comment has been deleted:
		if comment["deleted"]:
			comment["text"] = ""

	# creates a database connection:
	def __create_db_connection__(self):
		return factory.create_db_connection()


"""

## This class provides access to the data store for authenticated users.
#
#  The AuthenticatedApplication class provides nearly the same methods to access the
#  data store like the Application class. To get further information of a method please
#  have a look at the documentation of the Application class.
#
#  The main difference between both classes is that this one adds an authentication layer
#  to the application. Each request is validated by a checksum. To calculate this
#  checksum you have to order the parameters alphabetically. Then calculate the HMAC-SHA1
#  checksum using the hashed password (SHA-256) of the given user account. You find an
#  example algorithm in the utility module (util.sign_message).
class AuthenticatedApplication:
	def __init__(self):
		self.__app = None

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if not self.__app is None:
			del self.__app

	## Stores a user request in the data store.
	#  This method wraps Application::request_account().
	#  @param username name of the user to create
	#  @param email email address of the user
	#  @param user_request_timeout lifetime of the user request
	#  @return an auto-generated request code
	def request_account(self, username, email, user_request_timeout = config.USER_REQUEST_TIMEOUT):
		return self.__create_app__().request_account(username, email, user_request_timeout)

	## Generates a password request.
	#  This method wraps Application::request_password().
	#  @param username a user account
	#  @param email email address of the authenticated user account
	#  @return an auto-generated code
	def request_password(self, username, email):
		return self.__create_app__().request_password(username, email)

	## Generates a new password using a request code generated by the AuthenticatedApplication::request_password() method.
	#  This method wraps Application::generate_password().
	#  @param code a password request code
	#  @return username, email address & password (plaintext)
	def generate_password(self, code):
		return self.__create_app__().generate_password(code)

	## Activates a user account using an auto-generated request code.
	#  This method wraps Application::activate_user().
	#  @param code a request code generated by the AuthenticatedApplication::request_account() method
	#  @return username, email & password (plaintext)
	def activate_user(self, code):
		return self.__create_app__().activate_user(code)

	## Disables a user account.
	#  This method wraps Application::disable_user().
	#  @param req request data
	#  @param email email address of the authenticated user
	def disable_user(self, req, email):
		self.verify_message(req, email = email)

		app = self.__create_app__()
		user = app.get_active_user(req.username)

		if user["email"] != email:
			raise exception.InvalidEmailAddressException()

		app.disable_user(req.username)

	## Changes the password of a user account.
	#  This method wraps Application::change_password().
	#  @param req request data
	#  @param old_password old password (plaintext) of the authenticated account
	#  @param new_password a new password (plaintext) to set
	def change_password(self, req, old_password, new_password):
		self.verify_message(req, old_password = old_password, new_password = new_password)
		self.__create_app__().change_password(req.username, old_password, new_password)

	## Updates the details of a user account.
	#  This method wraps Application::update_user_details().
	#  @param req request data
	#  @param email email address to set
	#  @param firstname firstname to set
	#  @param lastname lastname to set
	#  @param gender gender to set
	#  @param language language to set
	#  @param protected protected status to set
	def update_user_details(self, req, email, firstname, lastname, gender, language, protected):
		self.verify_message(req, email = email, firstname = firstname, lastname = lastname, gender = gender, language = language, protected = protected)
		self.__create_app__().update_user_details(req.username, email, firstname, lastname, gender, language, protected)

	## Updates the avatar of a user account.
	#  This method wraps Application::update_avatar().
	#  @param req request data
	#  @param filename filename of the image
	#  @param stream input stream for reading image data
	def update_avatar(self, req, filename, stream):
		self.verify_message(req, filename = filename)
		self.__create_app__().update_avatar(req.username, filename, stream)

	## Finds users by search query.
	#  This method wraps Application::find_user().
	#  @param req request data
	#  @param query a search query
	#  @return an array
	def find_user(self, req, query):
		self.verify_message(req, query = query)

		return self.__create_app__().find_user(req.username, query)

	## Gets details of a user account depending on protected status & friendship.
	#  This method wraps Application::get_user_details().
	#  @param req request data
	#  @param name user to get details from
	#  @return a dictionary
	def get_user_details(self, req, name):
		self.verify_message(req, name = name)

		return self.__create_app__().get_user_details(req.username, name)

	## Gets object details.
	#  This method wraps Application::get_object().
	#  @param req request data
	#  @param guid guid of an object
	#  @return a dictionary
	def get_object(self, req, guid):
		self.verify_message(req, guid = guid)

		return self.__create_app__().get_object(guid)

	## Gets objects from the data store.
	#  This method wraps Application::get_objects().
	#  @param req request data
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array
	def get_objects(self, req, page, page_size):
		self.verify_message(req, page = page, page_size = page_size)

		return self.__create_app__().get_objects(page, page_size)

	## Gets objects assigned to a tag.
	#  This method wraps Application::get_tagged_objects().
	#  @param req request data
	#  @param tag tag to search
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array
	def get_tagged_objects(self, req, tag, page, page_size):
		self.verify_message(req, tag = tag, page = page, page_size = page_size)

		return self.__create_app__().get_tagged_objects(tag, page, page_size)

	## Gets the most popular objects.
	#  This method wraps Application::get_popular_objects().
	#  @param req request data
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array
	def get_popular_objects(self, req, page, page_size):
		self.verify_message(req, page = page, page_size = page_size)

		return self.__create_app__().get_popular_objects(page, page_size)

	## Gets random objects.
	#  This method wraps Application::get_random_objects().
	#  @param req request data
	#  @param page_size number of objects the method should(!) return
	#  @return an array
	def get_random_objects(self, req, page_size):
		self.verify_message(req, page_size = page_size)

		return self.__create_app__().get_random_objects(page_size)

	## Adds tags to an object.
	#  This method wraps Application::add_tags().
	#  @param req request data
	#  @param guid guid of an object
	#  @param tags array containing tags to add
	def add_tags(self, req, guid, tags):
		self.verify_message(req, guid = guid, tags = tags)
		self.__create_app__().add_tags(req.username, guid, tags)

	## Upvotes/Downvotes an object.
	#  This method wraps Application::rate().
	#  @param req request data
	#  @param guid guid of an object
	#  @param up True to upvote
	def rate(self, req, guid, up = True):
		self.verify_message(req, guid = guid, up = up)
		self.__create_app__().rate(req.username, guid, up)

	## Adds an object to the favorites list of a user.
	#  This method wraps Application::favor().
	#  @param req request data
	#  @param guid guid of an object
	#  @param favor True to add the object to the list
	def favor(self, req, guid, favor = True):
		self.verify_message(req, guid = guid, favor = favor)
		self.__create_app__().favor(req.username, guid, favor = favor)

	## Returns the favorites list of a user.
	#  This method wraps Application::get_favorites().
	#  @param req request data
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array
	def get_favorites(self, req, page, page_size):
		self.verify_message(req, page = page, page_size = page_size)

		return self.__create_app__().get_favorites(req.username, page, page_size)

	## Appends a comment to an object.
	#  This method wraps Application::add_comment().
	#  @param req request data
	#  @param guid guid of an object
	#  @param text text to append
	def add_comment(self, req, guid, text):
		self.verify_message(req, guid = guid, text = text)
		self.__create_app__().add_comment(guid, req.username, text)

	## Gets comments assigned to an object.
	#  This method wraps Application::get_comments().
	#  @param req request data
	#  @param guid guid of an object
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array
	def get_comments(self, req, guid, page, page_size):
		self.verify_message(req, guid = guid, page = page, page_size = page_size)

		return self.__create_app__().get_comments(guid, page, page_size)

	## Reports an object for abuse.
	#  This method wraps Application::report_abuse().
	#  @param req request data
	#  @param guid guid of an object
	#  @return True if the object has been reported
	def report_abuse(self, req, guid):
		self.verify_message(req, guid = guid)

		return self.__create_app__().report_abuse(guid)

	## Lets a user recommend an object to his/her friends.
	#  This method wraps Application::recommend().
	#  @param req request data
	#  @param guid guid of an object
	#  @param receivers array containing receiver names
	def recommend(self, req, guid, receivers):
		self.verify_message(req, guid = guid, receivers = receivers)
		self.__create_app__().recommend(req.username, guid, receivers)

	## Gets objects recommended to a user
	#  This method wraps Application::get_recommendations().
	#  @param req request data
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array
	def get_recommendations(self, req, page, page_size):
		self.verify_message(req, page = page, page_size = page_size)

		return self.__create_app__().get_recommendations(req.username, page, page_size)

	## Lets one user follow another user.
	#  This method wraps Application::follow().
	#  @param req request data
	#  @param user a user account the authenticated user wants to follow
	#  @param follow True to follow, False to unfollow
	def follow(self, req, user, follow):
		self.verify_message(req, user = user, follow = follow)
		self.__create_app__().follow(req.username, user, follow)

	## Gets messages sent to a user account.
	#  This method wraps Application::get_messages().
	#  @param req request data
	#  @param limit number of messages to receive
	#  @param older_than filter to get only messages older than the specified timestamp
	#  @return an array
	def get_messages(self, req, limit, older_than):
		self.verify_message(req, limit = limit, older_than = older_than)

		return self.__create_app__().get_messages(req.username, limit, older_than)

	## Validates a signature.
	#  @param req request data
	#  @param kwargs additional arguments
	def verify_message(self, req, **kwargs):
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

	## Gets the language of a user account.
	#  @param username name of a user account
	#  @return language of the user as string
	def get_user_language(self, username):
		user = self.__create_app__().get_full_user_details(username)

		if not user is None:
			if user["language"] is None:
				return config.DEFAULT_LANGUAGE

			return user["language"]

		raise exception.UserNotFoundException()

	def __get_user_password__(self, username):
		return self.__create_app__().get_password(username)

	def __create_app__(self):
		if self.__app is None:
			self.__app = Application()

		return self.__app
		"""
