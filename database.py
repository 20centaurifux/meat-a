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

## Database utility functions.
class DbUtil():
	__metaclass__ = abc.ABCMeta

	## Deletes data from all tables.
	@abc.abstractmethod
	def clear_tables(self): return

	## Closes the database connection.
	@abc.abstractmethod
	def close(self): return

## This class provides access to the user store.
class UserDb(object):
	__metaclass__ = abc.ABCMeta

	## Closes the database connection.
	@abc.abstractmethod
	def close(self): return

	## Returns user details.
	#  @param username user to get details from
	#  @return a dictionary holding user details ({ "name": str, "firstname": str, "lastname": str, "email": str,
	#                                               "password": str, "gender": str, "timestamp": float, "avatar": str,
	#                                               "blocked": bool, "protected": bool, "following": [ str, str, ... ],
	#                                               "language": str })
	@abc.abstractmethod
	def get_user(self, username): return None

	## Returns user details. Finds the user by his/her email address.
	#  @param email email address of a user account
	#  @return a dictionary holding user details ({ "name": str, "firstname": str, "lastname": str, "email": str,
	#                                               "password": str, "gender": str, "timestamp": float, "avatar": str,
	#                                               "blocked": bool, "protected": bool, "following": [ str, str, ... ],
	#                                               "language": str })
	@abc.abstractmethod
	def get_user_by_email(self, email): return None

	## Searches users by a given query.
	#  @param query a search query
	#  @return an array, each element is a dictionary holding user details ({ "name": str, "firstname": str, "lastname": str, "email": str,
	#                                                                         "gender": str, "timestamp": float, "avatar": str,
	#                                                                         "blocked": bool, "protected": bool, "following": [ str, str, ... ] })
	@abc.abstractmethod
	def search_user(self, query): return None

	## Creates a new user account.
	#  @param username unique username
	#  @param email unique email address
	#  @param password password of the new user
	#  @param firstname firstname of the new user
	#  @param lastname lastname of the new user
	#  @param gender gender of the new user ("m" or "f")
	#  @param language language of the new user (e.g. "en")
	#  @param protected protected status (if True only friends will see activities of the user account)
	@abc.abstractmethod
	def create_user(self, username, email, password, firstname = None, lastname = None, gender = None, language = None, protected = True): return

	## Updates a user account.
	#  @param username username of the account to update
	#  @param email unique email address to set
	#  @param firstname firstname to set
	#  @param lastname lastname to set
	#  @param gender gender to set
	#  @param language language to set
	#  @param protected protected status to set
	@abc.abstractmethod
	def update_user_details(self, username, email, firstname, lastname, gender, language, protected): return

	## Updates a user password.
	#  @param username username of a user account
	#  @param password password to set
	@abc.abstractmethod
	def update_user_password(self, username, password): return

	## Gets stored password of a user.
	#  @param username username of a user account
	#  @return a password
	@abc.abstractmethod
	def get_user_password(self, username): return None

	## Blocks/Unblocks a user account
	#  @param username username of a user account
	#  @param blocked True to block the account
	@abc.abstractmethod
	def block_user(self, username, blocked = True): return

	## Tests if a user is blocked.
	#  @param username username of the account to test
	#  @return True if the user is blocked
	@abc.abstractmethod
	def user_is_blocked(self, username): return

	## Updates the avatar of a user account.
	#  @param username username of a user account
	#  @param avatar avatar to set
	@abc.abstractmethod
	def update_avatar(self, username, avatar): return

	## Tests if a user exists in the user store.
	#  @param username username of a user account
	#  @return True if the account exists
	@abc.abstractmethod
	def user_exists(self, username): return False

	## Tests if an email address is assigned
	#  @param email email to set
	#  @return True if the email address is assigned
	@abc.abstractmethod
	def email_assigned(self, email): return False

	## Tests if a user request id does exist
	#  @param id request id to test
	#  @return True if the request code does exist
	@abc.abstractmethod
	def user_request_id_exists(self, code): return False

	## Gets data assigned to a user request code.
	#  @param id a user request id
	#  @return username and email address assigned to the request code
	@abc.abstractmethod
	def get_user_request(self, id): return None

	## Removes a user request.
	#  @param id id of the user request to remove
	@abc.abstractmethod
	def remove_user_request(self, id): return

	## Stores a user request in the data store.
	#  @param username requested username
	#  @param email email address of the requested account
	#  @param id the request id
	#  @param code the request code
	#  @param lifetime lifetime (in seconds) of the request
	@abc.abstractmethod
	def create_user_request(self, username, email, id, code, lifetime = 60): return

	## Tests if a username has already been requested.
	#  @param username username to test
	#  @return True if the username has been requested
	@abc.abstractmethod
	def username_requested(self, username): return False

	## Tests if a password request code does already exist.
	#  @param id request id to test
	#  @return True if the request code does exist
	@abc.abstractmethod
	def password_request_id_exists(self, id): return False

	## Gets data assigned to a password request.
	#  @param id a password request id
	#  @return username related to the password request code
	@abc.abstractmethod
	def get_password_request(self, id): return None

	## Removes a password request.
	#  @param id id of the password request to remove.
	@abc.abstractmethod
	def remove_password_request(self, id): return

	## Stores a password request in the data store.
	#  @param username name of the user who wants to reset his/her password
	#  @param id id of the request
	#  @param code code of the request
	#  @param lifetime lifetime (in seconds) of the request
	@abc.abstractmethod
	def create_password_request(self, username, id, code, lifetime = 60): return

	## Lets one user follow another user.
	#  @param user1 username of a user account
	#  @param user2 username of a user account
	#  @param follow True to let user1 follow user2
	@abc.abstractmethod
	def follow(self, user1, user2, follow = True): return

	## Tests if a user follows another user.
	#  @param user1 username of a user account
	#  @param user2 username of a user account
	#  @return True if user1 follows user2
	@abc.abstractmethod
	def is_following(self, user1, user2): return False

## This class provides access to the object store.
class ObjectDb(object):
	__metaclass__ = abc.ABCMeta

	## Closes the database connection.
	@abc.abstractmethod
	def close(self): return

	## Creates a new object.
	#  @param guid guid of the object
	#  @param source source of the object
	@abc.abstractmethod
	def create_object(self, guid, source): return

	## Locks an object.
	#  @param guid guid of the object to lock
	#  @param locked True to lock object
	@abc.abstractmethod
	def lock_object(self, guid, locked = True): return

	## Tests if an object is locked.
	#  @param guid guid of the object to test
	#  @return True if the object is locked
	@abc.abstractmethod
	def is_locked(self, guid): return False

	## Removes an object from the data store.
	#  @param guid guid of the object to remove
	@abc.abstractmethod
	def remove_object(self, guid): return

	## Tests if an object does exist.
	#  @param guid guid of the object to test
	#  @return True if the object does exist
	@abc.abstractmethod
	def object_exists(self, guid): return False

	## Gets details of an object.
	#  @param guid guid of an object
	#  @return a dictionary holding object details ({ "guid": str, "source": str, "locked": bool,
	#          "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int, "reported": bool })
	@abc.abstractmethod
	def get_object(self, guid): return None

	## Gets objects from the data store.
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_objects(self, page = 0, page_size = 10): return None

	## Gets objects assigned to a tag.
	#  @param tag tag to search
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_tagged_objects(self, tag, page = 0, page_size = 10): return None

	## Gets the most popular objects.
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_popular_objects(self, page = 0, page_size = 10): return None

	## Gets random objects.
	#  @param page_size number of objects the method should(!) return
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_random_objects(self, page_size = 10): return None

	## Adds tags to an object.
	#  @param guid guid of an object
	#  @param tags array containing tags to add
	@abc.abstractmethod
	def add_tags(self, guid, tags): return

	## Builds the tag statistic.
	@abc.abstractmethod
	def build_tag_statistic(self): return

	## Gets tag statistic.
	#  @param limit maximum number of tags to get
	#  @return an array, each element is a dictionary holding tag details ({ "name": str, "count": int })
	@abc.abstractmethod
	def get_tags(self, limit = None): return None

	## Upvotes/Downvotes an object.
	#  @param guid guid of an object
	#  @param username user who wants to vote
	#  @param up True to upvote
	@abc.abstractmethod
	def rate(self, guid, username, up = True): return

	## Tests if a user has already voted.
	#  @param guid guid of an object
	#  @param username username to test
	#  @return True if user has already voted
	@abc.abstractmethod
	def user_can_rate(self, guid, username): return False

	## Appends a comment to an object.
	#  @param guid guid of an object
	#  @param username author of the comment
	#  @param text text to append
	@abc.abstractmethod
	def add_comment(self, guid, username, text): return

	## Gets comments assigned to an object.
	#  @param guid guid of an object
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding a comment ({ "text": str, "timestamp": float,
	#          "user": { "name": str, "firstname": str, "lastname": str, "gender": str, "avatar": str, "blocked": bool })
	@abc.abstractmethod
	def get_comments(self, guid, page = 0, page_size = 10): return None

	## Adds an object to the favorites list of a user.
	#  @param guid guid of an object
	#  @param username user who wants to add the object to his/her favorites list
	#  @param favor True to add the object to the list
	@abc.abstractmethod
	def favor_object(self, guid, username, favor = True): return

	## Tests if an object is assigned to the favorites list of a user.
	#  @param guid guid of an object
	#  @param username username of a user account
	#  @return True if the object has been favored
	@abc.abstractmethod
	def is_favorite(self, guid, username): return False

	## Returns the favorites list of a user.
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_favorites(self, username, page = 0, page_size = 10): return None

	## Lets a user recommend an object to his/her friends.
	#  @param guid guid of an object
	#  @param username user who wants to recommend the object
	#  @param receivers array containing receiver names
	@abc.abstractmethod
	def recommend(self, guid, username, receivers): return

	## Gets objects recommended to a user
	#  @param username a user account
	#  @param page page number
	#  @param page_size size of each page
	#  @return an array, each element is a dictionary holding object details ({ "guid": str, "source": str,
	#          "locked": bool, "tags": [ str, str, ... ], "score": { "up": int, "down": int, "fav": int, "total": int },
	#          "timestamp": float, "comments_n": int })
	@abc.abstractmethod
	def get_recommendations(self, username, page = 0, page_size = 10): return None

	## Tests if an object has been recommended to a user.
	#  @param guid guid of an object
	#  @param username username of a user account
	#  @return True if the object has already been recommended to the specified user
	@abc.abstractmethod
	def recommendation_exists(self, guid, username): return False

	## Reports an object for abuse.
	#  @param guid guid of an object
	@abc.abstractmethod
	def report(self, guid): return

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
