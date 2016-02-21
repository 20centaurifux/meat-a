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
#  @file controller.py
#  Controller classes.

## @package controller
#  Controller classes.

import config, app, view, exception, util, template, factory, re, sys, inspect
from base64 import b64decode, b64encode

## Converts an exception to a view.JSONView.
#  @param e an exception
#  @return a view.JSONView instance
def exception_to_json_view(e):
	if not isinstance(e, exception.BaseException):
		e = exception.InternalFailureException(str(e))

	m = {}
	m["message"] = e.message

	v = view.JSONView(e.http_status)
	v.bind(m)

	if e.http_status == 401:
		v.headers["WWW-Authenticate"] = "Basic realm=\"%s\"" % (b64encode(config.REALM))

	return v

## Converts an exception to a view.HTMLTemplateView.
#  @param e an exception
#  @return a view.HTMLTemplateView instance
def exception_to_html_view(e):
	if not isinstance(e, exception.BaseException):
		e = exception.InternalFailureException(str(e))

	v = view.HTMLTemplateView(e.http_status, template.MessagePage, config.DEFAULT_LANGUAGE)
	v.bind({"title": "Exception", "message": e.message})

	if e.http_status == 401:
		v.headers["WWW-Authenticate"] = "Basic realm=\"%s\"" % (b64encode(config.REALM))

	return v

## Controller base class.
class Controller:
	def __init__(self, exception_handler=exception_to_json_view):
		## An app.Application instance.
		self.app = app.Application()
		## Function to convert exceptions to a view.View instance.
		self.__exception_handler = exception_handler

	## Handles an HTTP request.
	#  @param method the HTTP method (post, get, put or delete)
	#  @param env a dictionary providing environment details
	#  @param kwargs received parameters
	#  @return a view.View instance with a binded model
	def handle_request(self, method, env, **kwargs):
		try:
			m = {"post": self.__post__, "get": self.__get__, "put": self.__put__, "delete": self.__delete__}

			self.__start_process__(env, **kwargs)

			f = m[method.lower()]

			# get function argument names:
			spec = inspect.getargspec(f)
			argnames = spec[0][2:]

			# get argument values from kwargs:
			values = util.select_values(kwargs, argnames)

			# set default values:
			defaults = spec[3]

			if not defaults is None:
				diff = len(values) - len(defaults)

				for i in range(len(values)):
					if values[i] is None and i >= diff:
						values[i] = defaults[diff - i]

			# merge argument list:
			args = [env] + values

			# call method:
			v = apply(f, args)

		except:
			v = self.__exception_handler(sys.exc_info()[1])

		return v

	def __method_not_supported__(self):
		return self.__exception_handler(exception.MethodNotSupportedException())

	def __start_process__(self, env, **kwargs):
		pass

	def __post__(self, env, *args):
		return self.__method_not_supported__()

	def __get__(self, env, *args):
		return self.__method_not_supported__()

	def __put__(self, env, *args):
		return self.__method_not_supported__()

	def __delete__(self, env, *args):
		return self.__method_not_supported__()

	def __test_required_parameters__(self, *params):
		for p in params:
			if p is None:
				raise exception.MissingParameterException()

## A controller with HTTP basic authentication support.
class AuthorizedController(Controller):
	def __init__(self ):
		Controller.__init__(self)

		self.username = None

	def __start_process__(self, env, **kwargs):
		# get & decode Authorization header:
		try:
			header = env["HTTP_AUTHORIZATION"]

			m = re.match("^Basic ([a-zA-Z0-9=/_\-]+)$", header)
			auth = b64decode(m.group(1))

			index = auth.find(":")

			if index == -1:
				raise exception.HTTPException(400, "Bad request. Authorization header is malformed.")

			self.username, password = auth[:index], auth[index + 1:]

		except KeyError:
			raise exception.AuthenticationFailedException()

		except:
			raise exception.HTTPException(400, "Bad request: Authorization header is malformed.")

		# validate password:
		authenticated = False

		try:
			authenticated = self.app.validate_password(self.username, password)

		except exception.UserNotFoundException:
			pass

		except exception.UserIsBlockedException:
			pass

		except:
			raise sys.exc_info()[1]

		if not authenticated:
			raise exception.NotAuthorizedException()

## Requests new user accounts.
class AccountRequest(Controller):
	def __init__(self):
		Controller.__init__(self)

	## Requests a user account.
	#  @param env environment data
	#  @param username name of the requested user account
	#  @param email email address of the requested user account
	#  @return URL if the registration website
	def __post__(self, env, username, email):
		self.__test_required_parameters__(username, email)

		id, code = self.app.request_account(username, email)

		url = util.build_url("/html/registration/%s", config.WEBSITE_URL, id)

		v = view.JSONView(201)
		v.headers["Location"] = url
		v.headers["ETag"] = util.hash(url)
		m = {"Location": url}
		v.bind(m)

		return v

## Activates requested user account with corresponding id & code.
class AccountActivation(Controller):
	def __init__(self):
		Controller.__init__(self, exception_to_html_view)

	## User activation website.
	#  @param env environment data
	#  @param id request id
	#  @param code activation code (optional)
	#  @return a website
	def __get__(self, env, id, code):
		self.__test_required_parameters__(id)

		with factory.create_db_connection() as connection:
			db = factory.create_user_db()

			with connection.enter_scope() as scope:
				if not db.user_request_id_exists(scope, id):
					raise exception.NotFoundException("Request id not found.")

		v = view.HTMLTemplateView(200, template.AccountActivationPage, config.DEFAULT_LANGUAGE)
		v.bind({"id": id, "code": code, "error_field": None})

		return v

	## Activates a user account.
	#  @param env environment data
	#  @param id request id
	#  @param code activation code
	#  @param new_password1 new password to set
	#  @param new_password2 repeated password
	#  @return a website displaying a success message or a website for entering the request code
	def __post__(self, env, id, code, new_password1, new_password2):
		self.__test_required_parameters__(id, code)

		tpl = template.AccountActivatedPage
		status = 200

		try:
			username, email, _ = self.app.activate_user(id, code)
			m = {"username": username}

		except exception.InvalidRequestCodeException as e:
			tpl = template.AccountActivationPage
			status = e.http_status
			m = {"id": id, "code": code, "error_field": "code"}

		v = view.HTMLTemplateView(status, tpl, config.DEFAULT_LANGUAGE)
		v.bind(m)

		return v

## Updates user password.
class UserPassword(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Updates the user password.
	#  @param env environment data
	#  @param old_password the current password
	#  @param new_password1 new password to set
	#  @param new_password2 repeated new password
	#  @return the new password (on success)
	def __post__(self, env, old_password, new_password1, new_password2):
		self.__test_required_parameters__(old_password, new_password1, new_password2)

		self.app.change_password(self.username, old_password, new_password1, new_password2)

		v = view.JSONView(200)
		m = {"password": new_password1}
		v.bind(m)

		return v

## Requests a new password.
class PasswordRequest(Controller):
	def __init__(self):
		Controller.__init__(self)

	## Requests a new password.
	#  @param env environment data
	#  @param username name of the user who wants to set a new password
	#  @param email the user's email address
	#  @return location of the generated resource to change the password
	def __post__(self, env, username, email):
		self.__test_required_parameters__(username, email)

		id, code = self.app.request_new_password(username, email)

		url = util.build_url("/html/user/%s/password/reset/%s", config.WEBSITE_URL, username, id)

		v = view.JSONView(201)
		v.headers["Location"] = url
		v.headers["ETag"] = util.hash(url)
		m = {"Location": url}
		v.bind(m)

		return v

## Resets a password using a corresponding code & id.
class PasswordChange(Controller):
	def __init__(self):
		Controller.__init__(self, exception_to_html_view)

	## A website to change the user's password.
	#  @param env environment data
	#  @param id password change request id
	#  @param code a related code (optional)
	#  @return a website
	def __get__(self, env, id, code):
		self.__test_required_parameters__(id)

		with factory.create_db_connection() as connection:
			db = factory.create_user_db()

			with connection.enter_scope() as scope:
				if not db.password_request_id_exists(scope, id):
					raise exception.NotFoundException("Request id not found.")

		v = view.HTMLTemplateView(200, template.ChangePasswordPage, config.DEFAULT_LANGUAGE)
		v.bind({"id": id, "code": code, "error_field": None})

		return v

	## Sets a new password.
	#  @param env environment data
	#  @param id password change request id
	#  @param code a related code
	#  @param new_password1 new password to set
	#  @param new_password2 repeated password
	#  @return a website displaying a success message or a website for entering the new password and request code
	def __post__(self, env, id, code, new_password1, new_password2):
		self.__test_required_parameters__(id, code)

		tpl = template.PasswordChangedPage
		status = 200

		try:
			username, _ = self.app.reset_password(id, code, new_password1, new_password2)
			m = {"username": username}

		except exception.BaseException as e:
			tpl = template.ChangePasswordPage
			status = e.http_status
			m = {"id": id, "code": code}

			if isinstance(e, exception.InvalidRequestCodeException):
				m["error_field"] = "code"
			elif isinstance(e, exception.InvalidParameterException):
				m["error_field"] = e.parameter
			else:
				raise e

		v = view.HTMLTemplateView(status, tpl, config.DEFAULT_LANGUAGE)
		v.bind(m)

		return v

## Updates, gets or deletes a user account.
class UserAccount(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Changes user details.
	#  @param env environment data
	#  @param email email address to set
	#  @param firstname firstname to set
	#  @param lastname lastname to set
	#  @param gender gender to set
	#  @param language language to set
	#  @param protected protected status to set
	#  @return new user details
	def __post__(self, env, email, firstname, lastname, gender, language, protected):
		self.__test_required_parameters__(email)

		self.app.update_user_details(self.username, email, firstname, lastname, gender, language, util.to_bool(protected))

		url = util.build_url("/account/%s", config.WEBSITE_URL, self.username)

		v = view.JSONView(200)
		m = self.app.get_full_user_details(self.username)
		v.bind(m)

		return v

	## Gets user details.
	#  @param env environment data
	#  @param username name of the user to get details from
	#  @return user details
	def __get__(self, env, username):
		self.__test_required_parameters__(username)

		if username.lower() == self.username.lower():
			m = self.app.get_full_user_details(username)
		else:
			m = self.app.get_user_details(self.username, username)

		v = view.JSONView(200)
		v.bind(m)

		return v

	## Disables a user account.
	#  @param env environment data
	#  @param username name of the user to deactivate
	#  @return no content (status 204)
	def __delete__(self, env, username):
		self.__test_required_parameters__(username)

		if not username.lower() == username:
			raise exception.NotAuthorizedException()

		self.app.disable_user(username)

		return view.EmptyView(204)

## Updates or downloads an avatar.
#  @todo not implemented yet
class Avatar(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __post__(self, env, *args):
		username, filename, stream = args

	def __get__(self, env, *args):
		username = args

## Searches the user database.
class Search(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Searches the user database.
	#  @param env environment data
	#  @param query search query
	#  @return a list with found usernames
	def __get__(self, env, query):
		m = self.app.find_user(self.username, query)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Updates or gets friendship details.
class Friendship(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets friendship details.
	#  @param env environment data
	#  @param username user to get friendship status from
	#  @return friendship details
	def __get__(self, env, username):
		self.__test_required_parameters__(username)

		return self.__get_friendship__(username)

	## Follows a user.
	#  @param env environment data
	#  @param username user to follow
	#  @return friendship details
	def __put__(self, env, username):
		self.__test_required_parameters__(username)

		return self.__change_friendship__(username, True)

	## Unfollows a user.
	#  @param env environment data
	#  @param username user to unfollow
	#  @return friendship details
	def __delete__(self, env, username):
		self.__test_required_parameters__(username)

		return self.__change_friendship__(username, False)

	def __change_friendship__(self, username, friendship):
		try:
			self.app.follow(self.username, username, friendship)

		except exception.ConflictException:
			pass

		except exception.NotFoundException:
			pass

		return self.__get_friendship__(username)

	def __get_friendship__(self, username):
		m = self.app.get_friendship(self.username, username)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets messages.
class Messages(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets messages.
	#  @param env environment data
	#  @param limit maximum number of received messages
	#  @param timestamp only get messages older than timestamp
	#  @return messages sent to the user account
	def __get__(self, env, limit=50, timestamp=None):
		m = self.app.get_messages(self.username, int(limit), timestamp)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets public messages.
class PublicMessages(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets public messages.
	#  @param env environment data
	#  @param limit maximum number of messages to receive
	#  @param timestamp only get messages older than timestamp
	#  @return public messages
	def __get__(self, env, limit=50, timestamp=None):
		m = self.app.get_public_messages(self.username, int(limit), timestamp)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets objects (ordered by timestamp).
class Objects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets objects.
	#  @param env environment data
	#  @param page page index
	#  @param page_size page size
	#  @return objects ordered by timestamp (descending)
	def __get__(self, env, page=0, page_size=10):
		m = self.app.get_objects(int(page), int(page_size))

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets random objects.
class RandomObjects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets random objects.
	#  @param env environment data
	#  @param page_size page size
	#  @return random objects
	def __get__(self, env, page_size=10):
		m = self.app.get_random_objects(int(page_size))

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets popular objects.
class PopularObjects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets popular objects.
	#  @param env environment data
	#  @param page page index
	#  @param page_size page size
	#  @return objects ordered by popularity
	def __get__(self, env, page=0, page_size=10):
		m = self.app.get_popular_objects(int(page), int(page_size))

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets objects filtered by tag.
class TaggedObjects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets objects assigned to a tag.
	#  @param env environment data
	#  @param tag a tag
	#  @param page page index
	#  @param page_size page size
	#  @return objects assigned to a tag
	def __get__(self, env, tag, page=0, page_size=10):
		m = self.app.get_tagged_objects(tag, int(page), int(page_size))

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets tag cloud.
class TagCloud(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets a tag cloud.
	#  @param env environment data
	#  @return a tag cloud
	def __get__(self, env):
		m = self.app.get_tag_cloud()

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets object details.
class Object(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets object details.
	#  @param env environment data
	#  @param guid guid of the object to get details from
	#  @return object details
	def __get__(self, env, guid):
		self.__test_required_parameters__(guid)

		m = self.app.get_object(guid)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets or sets object tag(s).
class ObjectTags(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets the tags assigned to an object.
	#  @param env environment data
	#  @param guid guid of the object to get tags from
	#  @return a tag list
	def __get__(self, env, guid):
		self.__test_required_parameters__(guid)

		return self.__get_tags__(guid)

	## Assigns tags to an object.
	#  @param env environment data
	#  @param guid guid of the object to tag
	#  @param tags comma-separated list of tags
	#  @return a tag list
	def __put__(self, env, guid, tags):
		self.__test_required_parameters__(guid, tags)

		tags = list(util.split_strip_set(tags, ","))

		if len(tags) == 0:
			raise exception.HTTPException(400, "tag list cannot be empty.")

		self.app.add_tags(guid, self.username, tags)

		return self.__get_tags__(guid)

	def __get_tags__(self, guid):
		obj = self.app.get_object(guid)
		m = obj["tags"]

		v = view.JSONView(200)
		v.bind(m)

		return v

## Votes object.
class Voting(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets the user's vote.
	#  @param env environment data
	#  @param guid object guid
	#  @return the vote
	def __get__(self, env, guid):
		self.__test_required_parameters__(guid)

		return self.__get_voting__(guid)

	## Votes an object.
	#  @param env environment data
	#  @param guid object guid
	#  @param up up or downvote flag
	#  @return the vote
	def __post__(self, env, guid, up):
		self.__test_required_parameters__(guid, up)

		self.app.vote(self.username, guid, util.to_bool(up))

		return self.__get_voting__(guid)

	def __get_voting__(self, guid):
		up = self.app.get_voting(self.username, guid)

		m = { "up": up }

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets or adds comment(s).
class Comments(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets object comments.
	#  @param env environment data
	#  @param guid guid of an object
	#  @param page page index
	#  @param page_size page size
	#  @return object comments
	def __get__(self, env, guid, page=0, page_size=50):
		self.__test_required_parameters__(guid)

		return self.__get_comments__(guid, page, page_size)

	## Adds a comment to an object.
	#  @param env environment data
	#  @param guid guid of an object
	#  @param text the comment
	#  @return object comments
	def __post__(self, env, guid, text):
		self.__test_required_parameters__(guid, text)

		self.app.add_comment(guid, self.username, text)

		return self.__get_comments__(guid)

	def __get_comments__(self, guid, page=0, page_size=50):
		self.__test_required_parameters__(guid)

		m = self.app.get_comments(guid, self.username, page, page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets a single comment.
class Comment(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets a single comment.
	#  @param env environment data
	#  @param id id of the comment to get
	#  @return a comment
	def __get__(self, env, id):
		self.__test_required_parameters__(id)

		m = self.app.get_comment(int(id), self.username)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets or updates favorites.
class Favorites(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets the favorites of the user.
	#  @param env environment data
	#  @return the user's favorite list
	def __get__(self, env):
		return self.__get_favorites__()

	## Adds an object to the user's favorite list.
	#  @param env environment data
	#  @param guid guid of the object to add
	#  @return the user's favorite list
	def __put__(self, env, guid):
		self.__test_required_parameters__(guid)

		return self.__change_favorite__(guid, True)

	## Removes an object from the user's favorite list.
	#  @param env environment data
	#  @param guid guid of the object to remove
	#  @return the user's favorite list
	def __delete__(self, env, guid):
		return self.__change_favorite__(guid, False)

	def __change_favorite__(self, guid, favorite):
		try:
			self.app.favor(self.username, guid, favorite)

		except exception.ConflictException:
			pass

		except exception.NotFoundException:
			pass

		return self.__get_favorites__()

	def __get_favorites__(self):
		m = self.app.get_favorites(self.username)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Gets recommendations.
class Recommendations(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Gets objects recommended to the user.
	#  @param env environment data
	#  @param page page index
	#  @param page_size page size
	#  @return recommended objects
	def __get__(self, env, page=0, page_size=10):
		m = self.app.get_recommendations(self.username, page, page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

## Recommends an object.
class Recommendation(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Recommends an object to other users.
	#  @param env environment data
	#  @param guid guid of the object to recommend
	#  @param receivers comma-separated list of users to recommend the object to
	#  @return users the object has been recommended to
	def __put__(self, env, guid, receivers):
		self.__test_required_parameters__(guid, receivers)

		receivers = list(util.split_strip_set(receivers, ","))

		if len(receivers) == 0:
			raise exception.HTTPException(400, "receiver list cannot be empty.")

		self.app.recommend(self.username, receivers, guid)

		m = { "guid": guid, "receivers": receivers }

		v = view.JSONView(200)
		v.bind(m)

		return v

## Flags object abused.
class ReportAbuse(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	## Flags an object abused.
	#  @param env environment data
	#  @param guid of the object to flag
	#  @return abuse status
	def __put__(self, env, guid):
		self.__test_required_parameters__(guid)

		self.app.report_abuse(guid)

		m = { "guid": guid, "reported": True }

		v = view.JSONView(200)
		v.bind(m)

		return v
