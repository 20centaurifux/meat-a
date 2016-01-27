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
#  Controller functions. Each function is assigned to a URL and returns a view.View instance.

## @package controller
#  Controller functions. Each function is assigned to a URL and returns a view.View instance.

import config, app, view, exception, util, re, sys, inspect
from base64 import b64decode, b64encode

def exception_to_view(e):
	if not isinstance(e, exception.BaseException):
		e = exception.InternalFailureException(str(e))

	m = {}
	m["message"] = e.message

	v = view.JSONView(e.http_status)
	v.bind(m)

	if e.http_status == 401:
		v.headers["WWW-Authenticate"] = "Basic realm=\"%s\"" % (b64encode(config.REALM))

	return v

class Controller:
	def __init__(self):
		self.app = app.Application()

	def __process__(self, method, env, **kwargs):
		try:
			m = { "post": self.__post__, "get": self.__get__, "put": self.__put__, "delete": self.__delete__ }

			self.__start_process__(env, **kwargs)

			f = m[method]

			# get function argument names:
			argnames = inspect.getargspec(f)[0][2:]

			# get argument values from kwargs:
			values = util.select_keys(kwargs, argnames)

			# merge argument list:
			args = [env] + values

			# call method:
			v = apply(f, args)

		except:
			v = exception_to_view(sys.exc_info()[1])

		return v

	def __method_not_supported__(self):
		return exception_to_view(exception.MethodNotSupportedException())

	def __start_process__(self, env, **kwargs):
		pass

	def post(self, env, **kwargs):
		return self.__process__("post", env, **kwargs)

	def get(self, env, **kwargs):
		return self.__process__("get", env, **kwargs)

	def put(self, env, **kwargs):
		return self.__process__("put", env, **kwargs)

	def delete(self, env, **kwargs):
		return self.__process__("delete", env, **kwargs)

	def __post__(self, env, *args):
		return self.__method_not_supported__()

	def __get__(self, env, *args):
		return self.__method_not_supported__()

	def __put__(self, env, *args):
		return self.__method_not_supported__()

	def __delete__(self, env, *args):
		return self.__method_not_supported__()

class AuthorizedController(Controller):
	def __init__(self ):
		Controller.__init__(self)

		self.username = None

	def __start_process__(self, env, **kwargs):
		# get & decode Authorization header:
		try:
			header = env["Authorization"]

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

class AccountRequest(Controller):
	def __init__(self):
		Controller.__init__(self)

	def __post__(self, env, username, email):
		id, code = self.app.request_account(username, email)

		url = util.build_url("/account/request/%s", config.WEBSITE_URL, id)

		v = view.JSONView(201)
		v.headers["Location"] = url
		m = { "Location": url }
		v.bind(m)

		return v

class AccountActivation(Controller):
	def __init__(self):
		Controller.__init__(self)

	def __get__(self, env, id, code):
		pass # TODO

	def __post__(self, env, id, code):
		username, email, password = self.app.activate_user(id, code)
		url = util.build_url("/user/%s", config.WEBSITE_URL, username)

		v = view.JSONView(201)
		v.headers["Location"] = url
		m = { "Location": url }
		v.bind(m)

		return v

class UserPassword(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __post__(self, env, old_password, new_password1, new_password2):
		self.app.change_password(self.username, old_password, new_password1, new_password2)

		v = view.JSONView(200)
		m = { "password": new_password1 }
		v.bind(m)

		return v

class PasswordRequest(Controller):
	def __init__(self):
		Controller.__init__(self)

	def __get__(self, env, id, code):
		pass # TODO

	def __post__(self, env, username, email):
		id, code = self.app.request_new_password(username, email)

		url = util.build_url("/account/%s/change-password", config.WEBSITE_URL, id)

		v = view.JSONView(201)
		v.headers["Location"] = url
		m = { "Location": url }
		v.bind(m)

		return v

class PasswordChange(Controller):
	def __init__(self):
		Controller.__init__(self)

	def __post__(self, env, id, code, new_password1, new_password2):
		self.app.reset_password(id, code, new_password1, new_password2)

		v = view.JSONView(200)
		m = { "password": new_password1 }
		v.bind(m)

		return v

class UserAccount(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __post__(self, env, email, firstname, lastname, gender, language, protected):
		self.app.update_user_details(self.username, email, firstname, lastname, gender, language, protected)

		url = util.build_url("/account/%s", config.WEBSITE_URL, self.username)

		v = view.JSONView(200)
		v.headers["Location"] = url
		m = { "Location": url }
		v.bind(m)

		return v

	def __get__(self, env, username):
		if username.lower() == self.username.lower():
			m = self.app.get_full_user_details(username)
		else:
			m = self.app.get_user_details(self.username, username)

		v = view.JSONView(200)
		v.bind(m)

		return v

	def __delete__(self, env, username):
		if not username.lower() == username:
			raise exception.NotAuthorizedException()

		self.app.disable_user(username)

		v = view.JSONView(204)

		return v

class Avatar(AuthorizedController): # TODO
	def __init__(self):
		AuthorizedController.__init__(self)

	def __post__(self, env, *args):
		username, filename, stream = args

	def __get__(self, env, *args):
		username = args

class Search(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, query):
		m = self.app.find_user(self.username, query)

		v = view.JSONView(200)
		v.bind(m)

		return v

class Friendship(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, username):
		return self.__get_friendship__(username)

	def __post__(self, env, username):
		return self.__change_friendship__(username, True)

	def __delete__(self, env, username):
		return self.__change_friendship__(username, False)

	def __change_friendship__(self, username, friendship):
		self.app.follow(self.username, username, friendship)

		return self.__get_friendship__(username)

	def __get_friendship__(self, username):
		m = self.app.get_friendship(self.username, username)

		v = view.JSONView(200)
		v.bind(m)

		return v

class Messages(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, limit, timestamp):
		m = self.app.get_messages(self.username, limit, timestamp)

		v = view.JSONView(200)
		v.bind(m)

		return v

class PublicMessages(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, limit, timestamp):
		m = self.app.get_public_messages(self.username, limit, timestamp)

		v = view.JSONView(200)
		v.bind(m)

		return v

class Objects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, page, page_size):
		m = self.app.get_objects(page, page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

class RandomObjects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, page_size):
		m = self.app.get_random_objects(page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

class PopularObjects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, page, page_size):
		m = self.app.get_popular_objects(page, page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

class TaggedObjects(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, tag, page, page_size):
		m = self.app.get_tagged_objects(tag, page, page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

class TagCloud(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env):
		m = self.app.get_tag_cloud()

		v = view.JSONView(200)
		v.bind(m)

		return v

class Object(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, guid):
		m = self.app.get_object(guid)

		v = view.JSONView(200)
		v.bind(m)

		return v

class ObjectTags(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, guid):
		return self.__get_tags__(guid)

	def __put__(self, env, guid, tags):
		s = set()

		for tag in filter(lambda t: len(t) > 0, map(lambda t: t.strip(), tags.split(","))):
			s.add(tag)

		if len(s) == 0:
			raise exception.HTTPException(400, "tag list cannot be empty.")

		self.app.add_tags(guid, self.username, s)

		return self.__get_tags__(guid)

	def __get_tags__(self, guid):
		obj = self.app.get_object(guid)
		m = obj["tags"]

		v = view.JSONView(200)
		v.bind(m)

		return v

class Voting(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, guid):
		return self.__get_voting__(guid)

	def __post__(self, env, guid, up):
		self.app.vote(self.username, guid, up)

		return self.__get_voting__(guid)

	def __get_voting__(self, guid):
		up = self.app.get_voting(self.username, guid)

		m = { "up": up }

		v = view.JSONView(200)
		v.bind(m)

		return v

class Comments(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, guid, page, page_size):
		return self.__get_comments__(guid, page, page_size)

	def __post__(self, env, guid, text):
		self.app.add_comment(guid, self.username, text)

		return self.__get_comments__(guid)

	def __get_comments__(self, guid, page=0, page_size=100):
		m = self.app.get_comments(guid, self.username, page, page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

class Comment(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, id):
		m = self.app.get_comment(id, self.username)

		v = view.JSONView(200)
		v.bind(m)

		return v

class Favorites(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env):
		return self.__get_favorites__()

	def __post__(self, env, guid):
		return self.__change_favorite__(guid, True)

	def __delete__(self, env, guid):
		return self.__change_favorite__(guid, False)

	def __change_favorite__(self, guid, favorite):
		self.app.favor(self.username, guid, favorite)

		return self.__get_favorites__()

	def __get_favorites__(self):
		m = self.app.get_favorites(self.username)

		v = view.JSONView(200)
		v.bind(m)

		return v

class Recommendations(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __get__(self, env, page, page_size):
		m = self.app.get_recommendations(self.username, page, page_size)

		v = view.JSONView(200)
		v.bind(m)

		return v

class Recommendation(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __put__(self, env, guid, receivers):
		s = set()

		for receiver in filter(lambda r: len(r) > 0, map(lambda t: t.strip(), receivers.split(","))):
			s.add(receiver)

		self.app.recommend(self.username, s, guid)

		m = { "guid": guid, "receivers": list(s) }

		v = view.JSONView(200)
		v.bind(m)

		return v

class ReportAbuse(AuthorizedController):
	def __init__(self):
		AuthorizedController.__init__(self)

	def __put__(self, env, guid):
		self.app.report_abuse(guid)

		m = { "guid": guid, "reported": True }

		v = view.JSONView(200)
		v.bind(m)

		return v
