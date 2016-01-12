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

## Transaction scope.
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

	# marks a transaction completed:
	def complete(self):
		self.__completed = True

	## Adds an event listener to the TransactionScope instance.
	#  @param listener to add
	def add_listener(self, listener):
		self.__listener.append(listener)

	## Removes an event listener to the TransactionScope instance.
	#  @param listener to remove
	def remove_listener(self, listener):
		self.__listener.append(listener)

	## Gets the connection object associated with the TransactionScope instance.
	#  @return the associated database connection
	def connection(self):
		return self.connection

	@abc.abstractmethod
	def __enter_scope__(self): return

	@abc.abstractmethod
	def __leave_scope__(self, commit): return

	## Gets a driver specific connection handle.
	#  @return a driver specific connection handle
	@abc.abstractmethod
	def get_handle(self): return None

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

	## Called when the TransactionScope created in Connection::enter_scope() is entered.
	def scope_entered(self, scope): pass

	## Called when the TransactionScope created in Connection::enter_scope() is leaved.
	def scope_leaved(self, scope):
		self.__scope = None

## This class provides access to the user store.
class UserDb(object):
	__metaclass__ = abc.ABCMeta

	## @param scope a transaction scope
	#  @param id request id to test
	#  @return True if the request id does exist
	#
	#  Tests if a request id does exist.
	@abc.abstractmethod
	def user_request_id_exists(self, scope, id): return

	## @param scope a transaction scope
	#  @param id request id to test
	#  @return a dictionary holding user request details: { "request_id": str, "request_code": str,
	#          "username": str, "email": str, "created_on": datetime }
	#
	#  Tests if a request id does exist.
	@abc.abstractmethod
	def get_user_request(self, scope, id): return

	## @param scope a transaction scope
	#  @param username username to test
	#  @param email email to test
	#  @return True if the username or email address is already assigned
	#
	#  Tests if a username or email address is already assigned.
	@abc.abstractmethod
	def username_or_email_assigned(self, scope, username, email): return

	## @param scope a transaction scope
	#  @param id the request id
	#  @param code a related request code
	#  @param username name of the user account
	#  @param email email address of the user account
	#
	#  Stores a user request in the database.
	@abc.abstractmethod
	def create_user_request(self, scope, id, code, username, email): return

	## @param scope a transaction scope
	#  @param id a request id
	#  @param code a related request code
	#  @param password (hash) of the account
	#  @param salt password salt
	#  @return id id of the created user
	#
	#  Activates a user account by the related request id and code.
	@abc.abstractmethod
	def activate_user(self, scope, id, code, password, salt): return

	## @param scope a transaction scope
	#  @param username username to test
	#  @return True if the account does exist
	#
	#  Tests if a user account does exist.
	@abc.abstractmethod
	def user_exists(self, scope, username): return

	## @param scope a transaction scope
	#  @param username username to test
	#  @return True if the account is blocked
	#
	#  Tests if a user account is blocked.
	@abc.abstractmethod
	def user_is_blocked(self, scope, username): return

	## @param scope a transaction scope
	#  @param username name of the user to block
	#  @param True to block the account
	#
	#  Blocks or unblocks a user account.
	@abc.abstractmethod
	def block_user(self, scope, username, blocked): return

	## @param scope a transaction scope
	#  @param username name of the user to delete
	#  @param True to delete the account
	#
	#  Deletes/restores a user account.
	@abc.abstractmethod
	def delete_user(self, scope, username, deleted): return

	## @param scope a transaction scope
	#  @param username a user account
	#  @return user password and salt
	#
	#  Gets password and salt of a user account.
	@abc.abstractmethod
	def get_user_password(self, scope, username): return

	## @param scope a transaction scope
	#  @param username a user account
	#  @param password password to set
	#  @param salt salt to set
	#
	#  Updates a user password.
	@abc.abstractmethod
	def update_user_password(self, scope, username, password, salt): return

	## @param scope a transaction scope
	#  @param username a user account
	#  @return a dictionary holding user details: { "id": int, "username": str, "firstname": str,
	#          "lastname": str, "language": str, "gender": str, "password": str, "salt": str,
	#          "blocked": bool, "deleted": bool, "created_on": datetime, "blocked_on": datetime,
	#          "deleted_on": datetime, "protected": bool, "avatar": str }
	#
	#  Gets user details.
	@abc.abstractmethod
	def get_user(self, scope, username): return

	## @param scope a transaction scope
	#  @param username a user account
	#
	#  Removes all password requests of the given user account.
	@abc.abstractmethod
	def remove_password_requests_by_user_id(self, scope, user_id): return

	## @param scope a transaction scope
	#  @param id a password request id
	#  @return True if the password request id does exist
	#
	#  Tests if a password request id exists.
	@abc.abstractmethod
	def password_request_id_exists(self, scope, id): return

	## @param scope a transaction scope
	#  @param id a password request id
	#  @param id a related password request code
	#  @param user_id id of the related user account
	#
	#  Stores a password request in the database.
	@abc.abstractmethod
	def create_password_request(self, scope, id, code, user_id): return

	## @param scope a transaction scope
	#  @param id a password request id
	#  @return a dictionary holiding request details: { "request_id": str, "request_code": str,
	#          "user": { "username": str, "blocked": bool, "deleted": bool } }
	#
	#  Gets a password request from the database.
	@abc.abstractmethod
	def get_password_request(self, scope, id): return

	## @param scope a transaction scope
	#  @param id a password request id
	#  @param code a related password request code
	#  @param password new password (hash) to set
	#  @param salt new salt to set
	#
	#  Resets the password of the user who requested the given password reset id.
	@abc.abstractmethod
	def reset_password(self, scope, id, code, password, salt): return

	## @param scope a transaction scope
	#  @param username name of the account to update
	#  @param email email address to set
	#  @param firstname firstname to set
	#  @param lastname lastname to set
	#  @param gender gender to set
	#  @param language language to set
	#  @param protected protected status to set
	#
	#  Updates user details.
	@abc.abstractmethod
	def update_user_details(self, scope, username, email, firstname, lastname, gender, language, protected): return

	## @param scope a transaction scope
	#  @param username a username
	#  @param email email address to test
	#  @return True if the specified email address is available.
	#
	#  Tests if an email address is available for the specified user account.
	@abc.abstractmethod
	def user_can_change_email(self, scope, username, email): return

	## @param scope a transaction scope
	#  @param username a username
	#  @param filename filename to set
	#
	#  Updates the avatar of the given user account.
	@abc.abstractmethod
	def update_avatar(self, scope, username, filename): return

	## @param scope a transaction scope
	#  @param username a username
	#  @return an array containing usernames
	#
	#  Gets the usernames of the accounts the specified user is following.
	@abc.abstractmethod
	def get_followed_usernames(self, scope, username): return

	## @param scope a transaction scope
	#  @param username a username
	#  @param query a search quey
	#  @return an array containing usernames
	#
	#  Searches the database.
	@abc.abstractmethod
	def search(self, scope, query): return

## This class provides access to the object store.
class ObjectDb(object):
	__metaclass__ = abc.ABCMeta

	## Creates a new object.
	#  @param scope a transaction scope
	#  @param guid guid of the object
	#  @param source source of the object
	@abc.abstractmethod
	def create_object(self, scope, guid, source): return

	## Locks an object.
	#  @param scope a transaction scope
	#  @param guid guid of the object to lock
	#  @param locked True to lock object
	@abc.abstractmethod
	def lock_object(self, scope, guid, locked = True): return

	## Tests if an object is locked.
	#  @param scope a transaction scope
	#  @param guid guid of the object to test
	#  @return True if the object is locked
	@abc.abstractmethod
	def is_locked(self, scope, guid): return False

	## Removes an object from the data store.
	#  @param scope a transaction scope
	#  @param guid guid of the object to remove
	@abc.abstractmethod
	def remove_object(self, scope, guid): return

	## Tests if an object does exist.
	#  @param scope a transaction scope
	#  @param guid guid of the object to test
	#  @return True if the object does exist
	@abc.abstractmethod
	def object_exists(self, scope, guid): return False

	## Gets details of an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @return a dictionary holding object details ({ "guid": str, "source": str, "locked": bool,
	#          "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int, "reported": bool })
	@abc.abstractmethod
	def get_object(self, scope, guid): return None

	## Gets objects from the data store.
	#  @param scope a transaction scope
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_objects(self, scope, page = 0, page_size = 10): return None

	## Gets objects assigned to a tag.
	#  @param scope a transaction scope
	#  @param tag tag to search
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_tagged_objects(self, scope, tag, page = 0, page_size = 10): return None

	## Gets the most popular objects.
	#  @param scope a transaction scope
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_popular_objects(self, scope, page = 0, page_size = 10): return None

	## Gets random objects.
	#  @param scope a transaction scope
	#  @param page_size number of objects the method should(!) return
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_random_objects(self, scope, page_size = 10): return None

	## Adds tags to an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param tags array containing tags to add
	@abc.abstractmethod
	def add_tags(self, scope, guid, tags): return

	## Gets tag statistic.
	#  @param scope a transaction scope
	#  @param limit maximum number of tags to get
	#  @return an array, each element is a dictionary holding tag details ({ "name": str, "count": int })
	@abc.abstractmethod
	def get_tags(self, scope, limit = None): return None

	## Upvotes/Downvotes an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username user who wants to vote
	#  @param up True to upvote
	@abc.abstractmethod
	def rate(self, scope, guid, username, up = True): return

	## Tests if a user has already voted.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username username to test
	#  @return True if user has already voted
	@abc.abstractmethod
	def user_can_rate(self, scope, guid, username): return False

	## Appends a comment to an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username author of the comment
	#  @param text text to append
	@abc.abstractmethod
	def add_comment(self, scope, guid, username, text): return

	## Gets comments assigned to an object.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding a comment ({ "text": str, "timestamp": float,
	#          "user": { "name": str, "firstname": str, "lastname": str, "gender": str, "avatar": str, "blocked": bool })
	@abc.abstractmethod
	def get_comments(self, scope, guid, page = 0, page_size = 10): return None

	## Adds an object to the favorites list of a user.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username user who wants to add the object to his/her favorites list
	#  @param favor True to add the object to the list
	@abc.abstractmethod
	def favor_object(self, scope, guid, username, favor = True): return

	## Tests if an object is assigned to the favorites list of a user.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username username of a user account
	#  @return True if the object has been favored
	@abc.abstractmethod
	def is_favorite(self, scope, guid, username): return False

	## Returns the favorites list of a user.
	#  @param scope a transaction scope
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_favorites(self, scope, username, page = 0, page_size = 10): return None

	## Lets a user recommend an object to his/her friends.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username user who wants to recommend the object
	#  @param receivers array containing receiver names
	@abc.abstractmethod
	def recommend(self, scope, guid, username, receivers): return

	## Gets objects recommended to a user
	#  @param scope a transaction scope
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_recommendations(self, scope, username, page = 0, page_size = 10): return None

	## Tests if an object has been recommended to a user.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	#  @param username username of a user account
	#  @return True if the object has already been recommended to the specified user
	@abc.abstractmethod
	def recommendation_exists(self, scope, guid, username): return False

	## Reports an object for abuse.
	#  @param scope a transaction scope
	#  @param guid guid of an object
	@abc.abstractmethod
	def report(self, scope, guid): return

## This class provides access to the stream store.
class StreamDb(object):
	## Enumeration indicating the type of a message.
	MessageType = util.enum(RECOMMENDATION = 0, COMMENT = 1, FAVOR = 2, VOTE = 3, FOLLOW = 4, UNFOLLOW = 5)

	## Adds a message the stream store.
	#  @param code type of the nessage
	#  @param sender username of the sender
	#  @param receivers array containing receiver names
	#  @param args optional parameters depending on the message type
	@abc.abstractmethod
	def add_message(self, code, sender, receivers, **args): return

	## Gets messages assigned to a user.
	#  @param user name of a user account
	#  @param limit maximum number of messages to receive
	#  @param older_than filter to get only messages older than the given timeframe
	#  @return an array, each element is a dictionary holding a message ({ "type_id": int, "timestamp": float,
	#          "sender": { "name": str, "firstname": str, "lastname": str, "gender": str, "avatar": str, "blocked": bool },
	#          [ optional fields depending on message type] })
	@abc.abstractmethod
	def get_messages(self, user, limit = 100, older_than = None): return None

## This class provides access to the mail store.
class MailDb(object):
	## Appends a message to the mail store.
	#  @param subject subject of the mail
	#  @param body body of the mail
	#  @param receiver username of the receiver
	#  @param lifetime lifetime of the mail
	@abc.abstractmethod
	def append_message(self, subject, body, receiver, lifetime): return

	## Gets unsent messages.
	#  @param limit maximum numbers of messages to get
	#  @return an array, each element is a dictionary holding a message ({ "subject": str, "body": str, "receiver": str,
	#                                                                      "created": float })
	@abc.abstractmethod
	def get_unsent_messages(self, limit = 100): return None

	## Sets the "Sent" flag of a mail.
	#  @param id id of a mail
	@abc.abstractmethod
	def mark_sent(self, id): return

## This class is used to count HTTP requests.
class RequestDb(object):
	## Enumeration indicating the request type.
	RequestType = util.enum(ACCOUNT_REQUEST = 0, PASSWORD_RESET = 1, DEFAULT_REQUEST = 2)

	## Stores a request in the data store.
	#  @param code type of the request
	#  @param ip an IP address
	#  @param lifetime lifetime of the request (in seconds)
	@abc.abstractmethod
	def append_request(self, code, ip, lifetime = 3600): return

	## Counts requests filtered by IP address and request type.
	#  @param code type of the request
	#  @param ip an IP address
	#  @return an integer
	@abc.abstractmethod
	def count_requests(self, code, ip): return 0

	## Removes expired requests.
	@abc.abstractmethod
	def remove_old_requests(self): return

	## Gets the total number of requests stored in the database.
	#  @return an integer
	@abc.abstractmethod
	def total_requests(self): return
