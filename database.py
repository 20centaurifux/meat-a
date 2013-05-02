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

import abc, util

class DbUtil():
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def clear_tables(self): return

	@abc.abstractmethod
	def close(self): return

class UserDb(object):
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def close(self): return

	@abc.abstractmethod
	def get_user(self, username): return None

	@abc.abstractmethod
	def get_user_by_email(self, email): return None

	@abc.abstractmethod
	def search_user(self, query): return None

	@abc.abstractmethod
	def create_user(self, username, email, password, firstname = None, lastname = None, gender = None, language = None, protected = True): return

	@abc.abstractmethod
	def update_user_details(self, username, email, firstname, lastname, gender, language, protected): return

	@abc.abstractmethod
	def update_user_password(self, username, password): return

	@abc.abstractmethod
	def get_user_password(self, username): return None

	@abc.abstractmethod
	def block_user(self, username, blocked = True): return

	@abc.abstractmethod
	def user_is_blocked(self, username): return

	@abc.abstractmethod
	def update_avatar(self, username, avatar): return

	@abc.abstractmethod
	def user_exists(self, username): return False

	@abc.abstractmethod
	def email_assigned(self, email): return False

	@abc.abstractmethod
	def user_request_code_exists(self, code): return False

	@abc.abstractmethod
	def get_user_request(self, code): return None

	@abc.abstractmethod
	def remove_user_request(self, code): return

	@abc.abstractmethod
	def create_user_request(self, username, email, code, lifetime = 60): return

	@abc.abstractmethod
	def username_requested(self, username): return False

	@abc.abstractmethod
	def password_request_code_exists(self, code): return False

	@abc.abstractmethod
	def get_password_request(self, code): return None

	@abc.abstractmethod
	def remove_password_request(self, code): return

	@abc.abstractmethod
	def create_password_request(self, username, code, lifetime = 60): return

	@abc.abstractmethod
	def follow(self, user1, user2, follow = True): return

	@abc.abstractmethod
	def is_following(self, user1, user2): return False

class ObjectDb(object):
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def close(self): return

	@abc.abstractmethod
	def create_object(self, guid, source): return

	@abc.abstractmethod
	def lock_object(self, guid, locked = True): return

	@abc.abstractmethod
	def is_locked(self, guid): return False

	@abc.abstractmethod
	def remove_object(self, guid): return

	@abc.abstractmethod
	def object_exists(self, guid): return False

	@abc.abstractmethod
	def get_object(self, guid): return None

	@abc.abstractmethod
	def get_objects(self, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def get_tagged_objects(self, tag, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def get_popular_objects(self, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def get_random_objects(self, page_size = 10): return None

	@abc.abstractmethod
	def add_tags(self, guid, tags): return

	@abc.abstractmethod
	def build_tag_statistic(self): return

	@abc.abstractmethod
	def get_tags(self, limit = None): return None

	@abc.abstractmethod
	def rate(self, guid, username, up = True): return

	@abc.abstractmethod
	def user_can_rate(self, guid, username): return False

	@abc.abstractmethod
	def add_comment(self, guid, username, text): return

	@abc.abstractmethod
	def get_comments(self, guid, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def favor_object(self, guid, username, favor = True): return

	@abc.abstractmethod
	def is_favorite(self, guid, username): return False

	@abc.abstractmethod
	def get_favorites(self, username, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def recommend(self, guid, username, receivers): return

	@abc.abstractmethod
	def get_recommendations(self, username, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def recommendation_exists(self, guid, username): return False

class StreamDb(object):
	MessageType = util.enum(RECOMMENDATION = 0, COMMENT = 1, FAVOR = 2, VOTE = 3, FOLLOW = 4, UNFOLLOW = 5)

	@abc.abstractmethod
	def add_message(self, code, sender, receivers, **args): return

	@abc.abstractmethod
	def get_messages(self, user, limit = 100, older_than = None): return None

class MailDb(object):
	@abc.abstractmethod
	def append_message(self, subject, body, receiver, lifetime): return

	@abc.abstractmethod
	def get_unsent_mails(self, limit = 100): return None

class RequestDb(object):
	RequestType = util.enum(ACCOUNT_REQUEST = 0, PASSWORD_RESET = 1)

	@abc.abstractmethod
	def append_request(self, code, ip, lifetime = 360): return

	@abc.abstractmethod
	def count_requests(self, code, ip, timeframe): return 0

	@abc.abstractmethod
	def remove_old_requests(self, timeframe): return

	@abc.abstractmethod
	def total_requests(self): return
