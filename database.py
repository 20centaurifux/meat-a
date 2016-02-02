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
#  @file database.py
#  Data layer base classes.

## @package database
#  Data layer base classes.

import abc, util

## Makes a code block transactional.
class TransactionScope():
	def __init__(self, connection):
		self.__completed = False
		self.__listener = []
		self.__conn = connection

	def __enter__(self):
		# call backend specific initialization & listener:
		self.__enter_scope__()

		for l in self.__listener:
			l.scope_entered(self)

		return self

	def __exit__(self, type, value, traceback):
		# call backend specific deinitialization & listener:
		self.__enter_scope__()
		self.__leave_scope__(self.__completed)

		for l in self.__listener:
			l.scope_leaved(self)

	# Indicates that all operation within the scope are completed successfully.
	def complete(self):
		self.__completed = True

	## Adds an event listener to the TransactionScope instance.
	#  @param listener to add
	def add_listener(self, listener):
		self.__listener.append(listener)

	## Removes an event listener from the TransactionScope instance.
	#  @param listener to remove
	def remove_listener(self, listener):
		self.__listener.append(listener)

	## Gets a driver specific connection handle.
	#  @return a driver specific connection handle
	@abc.abstractmethod
	def get_handle(self): return None

	@abc.abstractmethod
	def __enter_scope__(self): return

	@abc.abstractmethod
	def __leave_scope__(self, commit): return

## Database base class.
class Connection():
	__metaclass__ = abc.ABCMeta

	def __init__(self):
		self.__scope = None

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	## Starts a new transaction.
	#  @return a new TransactionScope instance
	def enter_scope(self):
		if self.__scope is not None:
			raise Exception("Cannot nest transaction scopes.")

		self.__scope = self.__create_transaction_scope__()
		self.__scope.add_listener(self)

		return self.__scope

	@abc.abstractmethod
	def __create_transaction_scope__(self): return None

	## Closes the database connection.
	@abc.abstractmethod
	def close(self): return

	## Called when the TransactionScope created with Connection::enter_scope() is entered.
	def scope_entered(self, scope): pass

	## Called when the TransactionScope created with Connection::enter_scope() is leaved.
	def scope_leaved(self, scope):
		self.__scope = None

## This class provides functions required for unit testing.
class TestDb(object):
	__metaclass__ = abc.ABCMeta

	## Deletes all data.
	#  @param scope a transaction scope
	@abc.abstractmethod
	def clear(self, scope): pass

## This class provides access to the user store.
class UserDb(object):
	__metaclass__ = abc.ABCMeta

	## Tests if a request id does exist.
	#  @param scope a transaction scope
	#  @param id request id to test
	#  @return True if the request id does exist
	@abc.abstractmethod
	def user_request_id_exists(self, scope, id): return None

	## Gets data associated to a request id.
	#  @param scope a transaction scope
	#  @param id a request id
	#  @return a dictionary holding user request details: { "request_id": str, "request_code": str,
	#          "username": str, "email": str, "created_on": datetime }
	@abc.abstractmethod
	def get_user_request(self, scope, id): return None

	## Tests if a username or email address is already assigned.
	#  @param scope a transaction scope
	#  @param username username to test
	#  @param email email to test
	#  @return True if the username or email address is already assigned
	@abc.abstractmethod
	def username_or_email_assigned(self, scope, username, email): return None

	## Stores a user request in the database.
	#  @param scope a transaction scope
	#  @param id the request id
	#  @param code a related request code
	#  @param username name of the user account
	#  @param email email address of the user account
	@abc.abstractmethod
	def create_user_request(self, scope, id, code, username, email): return None

	## Activates a user account by the related request id and code.
	#  @param scope a transaction scope
	#  @param id a request id
	#  @param code a related request code
	#  @param password (hash) of the account
	#  @param salt password salt
	#  @return id id of the created user
	@abc.abstractmethod
	def activate_user(self, scope, id, code, password, salt): return None

	## Tests if a user account does exist.
	#  @param scope a transaction scope
	#  @param username username to test
	#  @return True if the account does exist
	@abc.abstractmethod
	def user_exists(self, scope, username): return None

	## Maps a user id to the associated username.
	#  @param user_id id to map
	#  @return a username
	@abc.abstractmethod
	def map_user_id(self, scope, user_id): return None

	## Tests if a user account is blocked.
	#  @param scope a transaction scope
	#  @param username username to test
	#  @return True if the account is blocked
	@abc.abstractmethod
	def user_is_blocked(self, scope, username): return None

	## Blocks or unblocks a user account.
	#  @param scope a transaction scope
	#  @param username name of the user to block
	#  @param True to block the account
	@abc.abstractmethod
	def block_user(self, scope, username, blocked=True): pass

	## Deletes or restores a user account.
	#  @param scope a transaction scope
	#  @param username name of the user to delete
	#  @param True to delete the account
	@abc.abstractmethod
	def delete_user(self, scope, username, deleted=True): pass

	## Gets password and salt of a user account.
	#  @param scope a transaction scope
	#  @param username a user account
	#  @return user password and salt
	@abc.abstractmethod
	def get_user_password(self, scope, username): return None

	## Updates a user password.
	#  @param scope a transaction scope
	#  @param username a user account
	#  @param password password (hash) to set
	#  @param salt salt to set
	@abc.abstractmethod
	def update_user_password(self, scope, username, password, salt): pass

	## Gets user details.
	#  @param scope a transaction scope
	#  @param username a user account
	#  @return a dictionary holding user details: { "id", int, "username", str, "firstname", str,
	#          "lastname", str, "email", str, "gender", str, "created_on", datetime,
	#          "avatar": str, "protected": bool, "blocked": bool, "language": str }
	@abc.abstractmethod
	def get_user(self, scope, username): return None

	## Removes all password requests of the given user account.
	#  @param scope a transaction scope
	#  @param user_id a user id
	@abc.abstractmethod
	def remove_password_requests_by_user_id(self, scope, user_id): pass

	## Tests if a password request id exists.
	#  @param scope a transaction scope
	#  @param id a password request id
	#  @return True if the password request id does exist
	@abc.abstractmethod
	def password_request_id_exists(self, scope, id): return None

	## Stores a password request in the database.
	#  @param scope a transaction scope
	#  @param id a password request id
	#  @param code a related password request code
	#  @param user_id id of the related user account
	@abc.abstractmethod
	def create_password_request(self, scope, id, code, user_id): pass

	## Gets password request details from the database.
	#  @param scope a transaction scope
	#  @param id a password request id
	#  @return a dictionary holiding request details: { "request_id": str, "request_code": str,
	#          "username": str, "blocked": bool, "deleted": bool }
	@abc.abstractmethod
	def get_password_request(self, scope, id): return None

	## Resets the password of the user who has requested the given password request id.
	#  @param scope a transaction scope
	#  @param id a password request id
	#  @param code a related password request code
	#  @param password new password (hash) to set
	#  @param salt new salt to set
	@abc.abstractmethod
	def reset_password(self, scope, id, code, password, salt): pass

	## Updates user details.
	#  @param scope a transaction scope
	#  @param username username of the account to update
	#  @param email email address to set
	#  @param firstname firstname to set
	#  @param lastname lastname to set
	#  @param gender gender to set
	#  @param language language to set
	#  @param protected protected status to set
	@abc.abstractmethod
	def update_user_details(self, scope, username, email, firstname, lastname, gender, language, protected): pass

	## Tests if an email address is available for the specified user account.
	#  @param scope a transaction scope
	#  @param username a username
	#  @param email email address to test
	#  @return True if the specified email address is available.
	@abc.abstractmethod
	def user_can_change_email(self, scope, username, email): return None

	## Updates the avatar of the given user account.
	#  @param scope a transaction scope
	#  @param username a username
	#  @param filename filename to set
	@abc.abstractmethod
	def update_avatar(self, scope, username, filename): pass

	## Gets the usernames of the accounts the specified user is following.
	#  @param scope a transaction scope
	#  @param username a username
	#  @return an array containing usernames
	@abc.abstractmethod
	def get_followed_usernames(self, scope, username): return None

	## Searches the database.
	#  @param scope a transaction scope
	#  @param username a username
	#  @param query a search quey
	#  @return an array containing usernames
	@abc.abstractmethod
	def search(self, scope, query): return None

	## Tests if a user follows another user.
	#  @param scope a transaction scope
	#  @param user1 a user account
	#  @param user2 a user account
	#  @return True if user1 follows user2
	def is_following(self, scope, user1, user2): return None

	## Lets one user follow another user. The followed user receives a notification.
	#  @param scope a transaction scope
	#  @param user1_id id of the user who wants to follow another user
	#  @param user2_id id of the user account user1_id wants to follow
	#  @param follow True to follow, False to unfollow
	@abc.abstractmethod
	def follow(self, scope, user1_id, user2_id, follow): pass

	## Add an object to the list of favorites.
	#  @param scope a transaction scope
	#  @param user_id a user id
	#  @param guid guid of an object
	#  @param favor True to add the object to the list of favorites
	@abc.abstractmethod
	def favor(self, scope, user_id, guid, follow=True): return

	## Tests if an object is on the list of favorites.
	#  @param scope a transaction scope
	#  @param user_id a user id
	#  @param guid guid of an object
	#  @returns True if the object is on the list of favorites
	@abc.abstractmethod
	def is_favorite(self, scope, user_id, guid): return None

	## Gets all favorites of a user.
	#  @param scope a transaction scope
	#  @param user_id a user id
	#  @return an array, each element is a dictionary holding object details: { "guid": str,
	#          "source": str, "locked": bool, "reported": bool, "tags": [ str, str, ... ],
	#          "score": { "up": int, "down": int, "fav": int }, "created_on": datetime,
	#          "comments_n": int, "reported": bool }
	@abc.abstractmethod
	def get_favorites(self, scope, user_id): return None

	## Lets a user recommend an object to his/her friends. A notification is generated.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param user_id id of the user who wants to recommend the object
	#  @param receiver_id id of the user the object is recommended to
	@abc.abstractmethod
	def recommend(self, scope, guid, user_id, receiver_id): pass

	## Tests if an object has been recommended to a user.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param sender username of the account who has recommended the object
	#  @param receiver username of the account the object has been recommended to
	#  @return True if the object has already been recommended to the specified user
	@abc.abstractmethod
	def recommendation_exists(self, scope, sender, receiver, guid): return None

	## Gets objects recommended to a user
	#  @param scope a transaction scope
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details: { "guid": str,
	#          "source": str, "locked": bool, "reported": bool, "tags": [ str, str, ... ],
	#          "score": { "up": int, "down": int, "fav": int }, "created_on": datetime,
	#          "comments_n": int, "reported": bool, "username": str, "recommended_on": dattime }
	@abc.abstractmethod
	def get_recommendations(self, scope, username, page=0, page_size=10): return None

## This class provides access to the object store.
class ObjectDb(object):
	__metaclass__ = abc.ABCMeta

	## Creates a new object.
	#  @param scope a transaction scope
	#  @param guid guid of the object
	#  @param source source of the object
	@abc.abstractmethod
	def create_object(self, scope, guid, source): pass

	## Locks an object.
	#  @param scope a transaction scope
	#  @param guid guid of the object to lock
	#  @param locked True to lock object
	@abc.abstractmethod
	def lock_object(self, scope, guid, locked=True): pass

	## Tests if an object is locked.
	#  @param scope a transaction scope
	#  @param guid guid of the object to test
	#  @return True if the object is locked
	@abc.abstractmethod
	def is_locked(self, scope, guid): return None

	## Removes an object from the data store.
	#  @param scope a transaction scope
	#  @param guid guid of the object to remove
	#  @param deleted True to delete object
	@abc.abstractmethod
	def delete_object(self, scope, guid, deleted=True): pass

	## Tests if an object does exist.
	#  @param scope a transaction scope
	#  @param guid guid of the object to test
	#  @return True if the object does exist
	@abc.abstractmethod
	def object_exists(self, scope, guid): return None

	## Gets details of an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @return an array, each element is a dictionary holding object details: { "guid": str,
	#          "source": str, "locked": bool, "reported": bool, "tags": [ str, str, ... ],
	#          "score": { "up": int, "down": int, "fav": int }, "created_on": datetime,
	#          "comments_n": int, "reported": bool }
	@abc.abstractmethod
	def get_object(self, scope, guid): return None

	## Gets objects from the data store.
	#  @param scope a transaction scope
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details: { "guid": str,
	#          "source": str, "locked": bool, "reported": bool, "tags": [ str, str, ... ],
	#          "score": { "up": int, "down": int, "fav": int }, "created_on": datetime,
	#          "comments_n": int, "reported": bool }
	@abc.abstractmethod
	def get_objects(self, scope, page=0, page_size=10): return None

	## Gets objects associated to a tag.
	#  @param scope a transaction scope
	#  @param tag tag to search
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details: { "guid": str,
	#          "source": str, "locked": bool, "reported": bool, "tags": [ str, str, ... ],
	#          "score": { "up": int, "down": int, "fav": int }, "created_on": datetime,
	#          "comments_n": int, "reported": bool }
	@abc.abstractmethod
	def get_tagged_objects(self, scope, tag, page=0, page_size=10): return None

	## Gets the most popular objects.
	#  @param scope a transaction scope
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details: { "guid": str,
	#          "source": str, "locked": bool, "reported": bool, "tags": [ str, str, ... ],
	#          "score": { "up": int, "down": int, "fav": int }, "created_on": datetime,
	#          "comments_n": int, "reported": bool }
	@abc.abstractmethod
	def get_popular_objects(self, scope, page=0, page_size=10): return None

	## Gets random objects.
	#  @param scope a transaction scope
	#  @param page_size number of object to get
	#  @return an array, each element is a dictionary holding object details: { "guid": str,
	#          "source": str, "locked": bool, "reported": bool, "tags": [ str, str, ... ],
	#          "score": { "up": int, "down": int, "fav": int }, "created_on": datetime,
	#          "comments_n": int, "reported": bool }
	@abc.abstractmethod
	def get_random_objects(self, scope, page_size=10): return None

	## Adds tags to an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param user_id id of the user who adds the tag
	#  @param tag tag to add
	@abc.abstractmethod
	def add_tag(self, scope, guid, user_id, tag): pass

	## Gets tag statistic.
	#  @param scope a transaction scope
	#  @return an array, each element is a dictionary holding tag details:
	#          { "name": str, "count": int }
	@abc.abstractmethod
	def get_tags(self, scope): return None

	## Tests if a user has already voted.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username username to test
	#  @return True if user has already voted
	@abc.abstractmethod
	def user_can_vote(self, scope, guid, username): return None

	## Upvotes/downvotes an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username user who votes
	#  @param up True to upvote
	@abc.abstractmethod
	def vote(self, scope, guid, user_id, up=True): pass

	## Gets a user voting.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username a username
	#  @return True or False
	@abc.abstractmethod
	def get_voting(self, scope, guid, username): return None

	## Appends a comment to an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param user_id id of the author
	#  @param text text to append
	@abc.abstractmethod
	def add_comment(self, scope, guid, user_id, text): pass

	## Flag a comment deleted.
	#  @param scope a transaction scope
	#  @param id id of the comment to flag.
	@abc.abstractmethod
	def flag_comment_deleted(self, scope, id): pass

	## Gets comments assigned to an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding a comment: { "id": int, "text": str,
	#         "created_on": datetime, "author": str, "deleted": bool }
	@abc.abstractmethod
	def get_comments(self, scope, guid, page=0, page_size=100): return None

	## Gets the comment with the specific id.
	#  @param scope a transaction scope
	#  @param id id of the comment to get
	#  @return a dictionary holding a comment: { "id": int, "text": str, "created_on": datetime,
	#          "username": str, "deleted": bool, "object-guid": str }
	@abc.abstractmethod
	def get_comment(self, scope, id): return None

	## Tests if a comment does exist.
	#  @param scope a transaction scope
	#  @param id id of the comment to test
	#  @return True if the comment does exist
	@abc.abstractmethod
	def comment_exists(self, scope, id): return None

	## Reports an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	@abc.abstractmethod
	def report_abuse(self, scope, guid): return

## This class provides access to the stream store.
class StreamDb(object):
	## Gets messages assigned to a user.
	#  @param user name of a user account
	#  @param limit maximum number of messages to receive
	#  @param older_than filter to get only messages older than the given timeframe
	#  @return an array, each element is a dictionary holding a message: { "id": int,
	#          "target": str, "source": str, "type": str, "created_on": datetime }
	@abc.abstractmethod
	def get_messages(self, scope, user, limit=100, older_than=None): return None

	## Gets public messages.
	#  @param limit maximum number of messages to receive
	#  @param older_than filter to get only messages older than the given timeframe
	#  @return an array, each element is a dictionary holding a message: { "id": int,
	#          "target": str, "source": str, "type": str, "created_on": datetime }
	@abc.abstractmethod
	def get_public_messages(self, scope, limit=100, older_than=None): return None

## This class provides access to the mail store.
class MailDb(object):
	## Pushs a message to the mail queue.
	#  @param scope a transaction scope
	#  @param subject subject of the mail
	#  @param body body of the mail
	#  @param user_id user id of the receiver
	@abc.abstractmethod
	def push_user_mail(self, scope, subject, body, user_id): return

	## Pushs a message to the mail queue.
	#  @param scope a transaction scope
	#  @param subject subject of the mail
	#  @param body body of the mail
	#  @param mail mail address of the receiver
	@abc.abstractmethod
	def push_mail(self, scope, subject, body, mail): return

	## Gets unsent messages.
	#  @param scope a transaction scope
	#  @param limit maximum numbers of messages to get
	#  @return an array, each element is a dictionary holding an email: { "id": int,
	#          "subject": str, "body": str, "created_on": datetime, "email": str }
	@abc.abstractmethod
	def get_unsent_messages(self, scope, limit=100): return None

	## Sets the "sent" flag of an email.
	#  @param scope a transaction scope
	#  @param id id of the email to flag
	@abc.abstractmethod
	def mark_sent(self, scope, id): return
