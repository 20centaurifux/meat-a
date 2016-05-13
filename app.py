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

import factory, exception, util, config, tempfile, os, sys, template, mailer
from validators import *
from base64 import b64encode
from datetime import datetime

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
	#  @param user_id id of the user to map
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
					raise exception.ConflictException("Username or email already assigned.")

				# generate request id & code:
				id = util.generate_junk(config.REQUEST_ID_LENGTH)

				while self.__user_db.user_request_id_exists(scope, id):
					id = util.generate_junk(config.REQUEST_ID_LENGTH)

				code = util.generate_junk(config.REQUEST_CODE_LENGTH)

				# save user request:
				self.__user_db.create_user_request(scope, id, code, username, email)

				# generate mail:
				url = util.build_url("/html/registration/%s?code=%s", config.WEBSITE_URL, id, code)

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
				if not self.__user_db.user_request_id_exists(scope, id):
					raise exception.NotFoundException("Request not found.")

				request = self.__user_db.get_user_request(scope, id)

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
					raise exception.ConflictException("User is already blocked.")
				elif not details["blocked"] and not disabled:
					raise exception.ConflictException("User is not blocked.")

				self.__user_db.block_user(scope, username, disabled)

				tpl = template.AccountDisabledMail(self.__get_language__(details), disabled)
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
			raise exception.InvalidParameterException("new_password1")

		if new_password1 != new_password2:
			raise exception.InvalidParameterException("new_password2")

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
					raise exception.WrongPasswordException()

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
					raise exception.WrongEmailAddressException()

				# delete existing request ids:
				self.__user_db.remove_password_requests_by_user_id(scope, user["id"])

				# create request id & code:
				id = util.generate_junk(config.REQUEST_ID_LENGTH)

				while self.__user_db.password_request_id_exists(scope, id):
					id = util.generate_junk(config.REQUEST_ID_LENGTH)

				code = util.generate_junk(config.REQUEST_CODE_LENGTH)
				url = util.build_url("/html/user/%s/password/reset/%s?code=%s", config.WEBSITE_URL, username, id, code)

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
	#  @return username and new password
	def reset_password(self, id, code, new_password1, new_password2):
		# validate passwords:
		if not validate_password(new_password1):
			raise exception.InvalidParameterException("new_password1")

		if new_password1 != new_password2:
			raise exception.InvalidParameterException("new_password2")

		# reset password:
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				# find request id & test code:
				if not self.__user_db.password_request_id_exists(scope, id):
					raise exception.NotFoundException("Request not found.")

				request = self.__user_db.get_password_request(scope, id)
				username = request["user"]["username"]

				self.__test_active_user__(scope, username)

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

				return username, new_password1

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

		if not isinstance(protected, bool):
			if isinstance(protected, str) and (protected.lower() in ["true", "false"]):
				protected = util.to_bool(protected)
			else:
				raise exception.InvalidParameterException("protected")

		# update user details:
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				# test email
				if not self.__user_db.user_can_change_email(scope, username, email):
					raise exception.ConflictException("Email address is already assigned.")

				# update user details:
				self.__user_db.update_user_details(scope, username, email, firstname, lastname, gender, language, protected)

				scope.complete()

	## Updates the avatar of a user account.
	#  @param username a user account
	#  @param filename filename of the image
	#  @param stream input stream for reading image data
	def update_avatar(self, username, filename, stream):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				# test if user is active:
				self.__test_active_user__(scope, username)

				# validate image:
				if not validate_image_file(stream, config.AVATAR_MAX_FILESIZE, config.AVATAR_MAX_WIDTH, config.AVATAR_MAX_HEIGHT, config.AVATAR_FORMATS):
					raise exception.InvalidImageFormatException()

				# save avatar:
				avatar = util.save_avatar(stream)

				# update user profile:
				self.__user_db.update_avatar(scope, username, avatar)
				scope.complete()

				return avatar

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

				for k in ["id", "username", "firstname", "lastname", "email", "gender", "created_on", "avatar", "protected", "blocked", "language"]:
					user[k] = details[k]

				user["following"] = self.__user_db.get_followed_usernames(scope, username)

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

				return self.__get_user_details__(scope, account, username)

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

				# search users:
				laccount = account.lower()
				result = []

				for username in self.__user_db.search(scope, query):
					if username.lower() <> laccount:
						result.append(self.__get_user_details__(scope, account, username))

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
					raise exception.ConflictException("User is already following the specified account.")
				elif not follow and not is_following:
					raise exception.NotFoundException("Couldn't find followed user account.")

				details1 = db.get_user(scope, user1)
				details2 = db.get_user(scope, user2)

				db.follow(scope, details1["id"], details2["id"], follow)

				scope.complete()

	## Tests if two users are friends.
	#  @param user1 a username
	#  @param user2 a username
	#  @return a dictionary holding friendship details: { "following": bool, "followed": bool }
	def get_friendship(self, user1, user2):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				db = self.__user_db

				if user1 == user2:
					raise InvalidParameterException("user2")

				self.__test_active_user__(scope, user1)
				self.__test_active_user__(scope, user2)

				following = db.is_following(scope, user1, user2)
				followed = db.is_following(scope, user2, user1)

				return { "following": following, "followed": followed }

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
					raise exception.ConflictException("Guid already exists.")

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

	## Delete an object.
	#  @param guid guid of the object
	def delete_object(self, guid):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_object_exists__(scope, guid)
				self.__object_db.delete_object(scope, guid, True)

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
	def get_objects(self, page=0, page_size=10):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				return self.__object_db.get_objects(scope, page, page_size)

	## Gets the most popular objects.
	#  @param page page number
	#  @param page_size size of each page
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_popular_objects(self, page=0, page_size=10):
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
	def get_tagged_objects(self, tag, page=0, page_size=10):
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
	#  @param ignore_conflicts don't raise an exception if a conflict occurs
	def add_tags(self, guid, username, tags, ignore_conflicts=True):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)
				self.__test_writeable_object__(scope, guid)

				user = self.__user_db.get_user(scope, username)

				for tag in tags:
					if not validate_tag(tag):
						raise InvalidParameterException("tag")

					try:
						self.__object_db.add_tag(scope, guid, user["id"], tag)

					except exception.ConflictException as e:
						if not ignore_conflicts:
							raise e

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
				self.__test_active_user__(scope, username)
				self.__test_writeable_object__(scope, guid)

				if not self.__object_db.user_can_vote(scope, guid, username):
					raise exception.ConflictException("User already rated.")

				user = self.__user_db.get_user(scope, username)

				self.__object_db.vote(scope, guid, user["id"], up)

				scope.complete()

	## Gets the voting of a user for an object.
	#  @param username a username
	#  @param guid guid of an object
	#  @return True, False or None
	def get_voting(self, username, guid):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)
				self.__test_object_exists__(scope, guid)

				return self.__object_db.get_voting(scope, guid, username)

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
					raise exception.ConflictException("Favorite already exists.")
				elif not favor and not is_favorite:
					raise exception.NotFoundException("Favorite not found.")

				self.__user_db.favor(scope, user["id"], guid, favor)

				scope.complete()

	## Returns the favorites list of a user.
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return a dictionary holding object details: { "guid": str, "source": str, "locked": bool,
	#          "reported": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int },
	#          "created_on": datetime, "comments_n": int, "reported": bool }
	def get_favorites(self, username, page=0, page_size=10):
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
	def get_comments(self, guid, username, page=0, page_size=100):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)
				self.__test_object_exists__(scope, guid)

				user = self.__user_db.get_user(scope, username)
				comments = self.__object_db.get_comments(scope, guid, page, page_size)
				cache = UserCache(self.__user_db, username)

				for comment in comments:
					self.__prepare_comment__(scope, comment, cache)
				return comments

	## Gets a single comment.
	#  @param username user who wants to receive the comment
	#  @param id id of the comment
	#  @return a dictionary holding a comment, the received user details of the author
	#          depend on the friendship status: [ { "text": str, "timestamp": datetime, "deleted": bool,
	#          "user": { } } ]
	def get_comment(self, id, username):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				comment = self.__object_db.get_comment(scope, id)

				if comment is None or len(comment) == 0:
					raise exception.NotFoundException("Comment not found.")

				self.__prepare_comment_no_cache__(scope, comment, username)

				return comment

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

					self.__test_active_user__(scope, lname)
					details = self.__user_db.get_user(scope, lname)

					if details["protected"] and not self.__user_db.is_following(scope, lname, username):
						raise exception.NoFriendshipExpception()

					if details["blocked"]:
						raise exception.UserIsBlockedException("Destination user account is blocked: %s" % (r))

					if not self.__user_db.recommendation_exists(scope, username, r, guid):
						self.__user_db.recommend(scope, sender["id"], details["id"], guid)

					receiver_set.add(lname)

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
					r["from"] = cache.lookup(scope, r["username"])
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
				self.__test_object_exists__(scope, guid)
				self.__object_db.report_abuse(scope, guid)

				scope.complete()

	## Gets messages sent to a user account.
	#  @param username a user account
	#  @param limit number of messages to receive
	#  @param after filter to get only messages created after the given timestamp
	#  @return an array, each element is a dictionary holding a message ({ "type_id": int, "timestamp": float,
	#          "sender": { "name": str, "firstname": str, "lastname": str, "gender": str, "avatar": str, "blocked": bool },
	#          [ optional fields depending on message type] })
	def get_messages(self, username, limit=100, after=None):
		with self.__create_db_connection__() as conn:
			with conn.enter_scope() as scope:
				self.__test_active_user__(scope, username)

				messages = []
				cache = UserCache(self.__user_db, username)

				if after is not None:
					after = datetime.fromtimestamp(int(after))

				for msg in self.__stream_db.get_messages(scope, username, limit, after):
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
				self.__test_active_user__(scope, username)

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
				raise exception.NotFoundException("Comment not found.")

			comment = self.__object_db.get_comment(scope, id)
			self.__prepare_comment__(scope, comment, cache)

			guid = comment["object-guid"]

			comment["object"] = self.__object_db.get_object(scope, guid)

			del comment["object-guid"]

			msg["target"] = comment

		elif m["type"] == "voted-object":
			guid = m["target"]
			self.__test_object_exists__(scope, guid)

			obj = self.__object_db.get_object(scope, guid)
			voting = self.__object_db.get_voting(scope, m["target"], source["username"])

			msg["target"] = { "object": obj, "voting": voting }

		return msg

	def __prepare_comment_no_cache__(self, scope, comment, username):
		# set author's user details:
		comment["user"] = self.__get_user_details__(scope, username, comment["username"])
		del comment["username"]

		self.__prepare_comment_text__(comment)

	def __prepare_comment__(self, scope, comment, cache):
		# set author's user details:
		comment["user"] = cache.lookup(scope, comment["username"])
		del comment["username"]

		self.__prepare_comment_text__(comment)

	def __prepare_comment_text__(self, comment):
		# clear text if comment has been deleted:
		if comment["deleted"]:
			comment["text"] = ""

	# creates a database connection:
	def __create_db_connection__(self):
		return factory.create_db_connection()
