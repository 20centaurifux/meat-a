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
#  @file wsgi.py
#  The WSGI application.

## @package wsgi
#  The WSGI application.

## @mainpage
#  <p>meat-a is a WSGI based webservice for the organization of objects and
#  related meta data.</p>
#
#  <p>Each object is stored in a data store (database.ObjectDb). Objects are
#  referenced by their guid and have a source. You can e.g. store links to
#  images in the data store.</p>
#
#  <p>The web interface provides the functionality to let multiple users share
#  meta data. Objects can be tagged and rated. Users can also add objects to
#  their personal favorite list and recommend them to other users.</p>
#
#  <p>Users can follow each other. If user A follows user B and user B also
#  follows user A they are friends. Friends can recommend objects to each
#  other. If a user profile is not protected every user can recommend objects
#  to the user.</p>
#
#  <p>Users are organized in a separate user store (database.UserDb).</p>
#
#  <p>Several activities generate notifications. If a user adds an object to
#  his/her favorites friends will receive a notification. If the user profile
#  is not protected every user following the account will get a notification.
#  Like other objects notifications are stored in separate data store
#  (database.StreamDb).</p>
#
#  <p>Sometimes a user will receive an email. If you're going to create a new user
#  profile a request code will be sent by email for example. Emails are stored
#  in the database.MailDb data store.</p>
#
#  <p>A service (mailer.Mailer) sends emails in a user-defined interval. This
#  process can also be triggered via a simple UDP request.</p>
#
#  <p>The different data stores can be accessed through the app.Application class.
#  The app.AuthenticatedApplication wraps the methods of the app.Application
#  class and tests additionally if a request is authenticated.</p>
#
#  <p>The authentication mechanism is quite simple. A request must contain at
#  least the username of a valid account and the current UNIX timestamp (UTC).
#  All parameters need to be sorted alphabetically. Then the HMAC-SHA1 checksum
#  has to be calculated. The required secret is the SHA-256 checksum of the
#  user password. You can find an example here: util.sign_message()</p>
#
#  <p>There's also an example client available: client.Client</p>
#
#  <p>The wsgi module tries to map a received path to a controller function.
#  Each controller returns a view.View object which will be used to generate
#  the response. The controller functions use an app.AuthenticatedApplication
#  instance to access the different data stores.</p>
#
#  <p>Data is stored with a MongoDB server but it's simple to use a different
#  backend.</p>
#
#  <p>To test the available modules just execute the test.py file.</p>
#
#  <p>To configure the service please have a look at the config module.</p>
#
#  <p>Have fun!</p>

import urlparse, config, exception, controller, logging, traceback
from app import AuthenticatedApplication
from cgi import FieldStorage

## An app.AuthenticatedApplication instance.
application = AuthenticatedApplication()

## Dictionary defining urls, their related controllers, required parameters & the allowed request method ("POST" or "GET").
routing = { "/account/new": { "controller": controller.request_account, "method": "POST", "params": [ "username", "email" ] },
            "/account/activate": { "controller": controller.activate_account, "method": "GET", "params": [ "code" ] },
            "/account/disable": { "controller": controller.disable_account, "method": "POST", "params": [ "username", "timestamp", "signature", "email" ] },
            "/account/password/update": { "controller": controller.update_password, "method": "POST", "params": [ "username", "timestamp", "signature", "old_password", "new_password" ] },
            "/account/password/request": { "controller": controller.request_password, "method": "GET", "params": [ "username", "email" ] },
            "/account/password/reset": { "controller": controller.password_reset, "method": "GET", "params": [ "code" ] },
            "/account/update": { "controller": controller.update_user_details,
	                         "method": "POST",
	                         "params": [ "username", "timestamp", "signature", "email", "firstname", "lastname", "gender", "language", "protected" ] },
            "/account/avatar/update": { "controller": controller.update_avatar,
	                         "method": "POST",
	                         "multipart": True,
	                         "params": [ "username", "timestamp", "signature", "filename", "file" ],
	                         "file_param": "file" },
            "/account/favorites": { "controller": controller.get_favorites, "method": "POST", "params": [ "username", "timestamp", "signature", "page", "page_size" ] },
            "/account/details": { "controller": controller.get_user_details, "method": "POST", "params": [ "username", "timestamp", "signature", "name" ] },
            "/account/follow": { "controller": controller.follow, "method": "POST", "params": [ "username", "timestamp", "signature", "user", "follow" ] },
            "/account/search": { "controller": controller.search_user, "method": "POST", "params": [ "username", "timestamp", "signature", "query" ] },
            "/account/recommendations": { "controller": controller.get_recommendations, "method": "POST", "params": [ "username", "timestamp", "signature", "page", "page_size" ] },
            "/account/messages": { "controller": controller.get_messages, "method": "POST", "params": [ "username", "timestamp", "signature", "limit", "older_than" ] },
            "/objects": { "controller": controller.get_objects, "method": "POST", "params": [ "username", "timestamp", "signature", "page", "page_size" ] },
            "/objects/tag": { "controller": controller.get_tagged_objects, "method": "POST", "params": [ "username", "timestamp", "signature", "tag", "page", "page_size" ] },
            "/objects/popular": { "controller": controller.get_popular_objects, "method": "POST", "params": [ "username", "timestamp", "signature", "page", "page_size" ] },
            "/objects/random": { "controller": controller.get_random_objects, "method": "POST", "params": [ "username", "timestamp", "signature", "page_size" ] },
            "/object/details": { "controller": controller.get_object, "method": "POST", "params": [ "username", "timestamp", "signature", "guid" ] },
            "/object/tags/add": { "controller": controller.add_tags, "method": "POST", "params": [ "username", "timestamp", "signature", "guid", "tags" ] },
            "/object/rate": { "controller": controller.rate, "method": "POST", "params": [ "username", "timestamp", "signature", "guid", "up" ] },
            "/object/favor": { "controller": controller.favor, "method": "POST", "params": [ "username", "timestamp", "signature", "guid", "favor" ] },
            "/object/comments/add": { "controller": controller.add_comment, "method": "POST", "params": [ "username", "timestamp", "signature", "guid", "text" ] },
            "/object/comments": { "controller": controller.get_comments, "method": "POST", "params": [ "username", "timestamp", "signature", "guid", "page", "page_size" ] },
            "/object/recommend": { "controller": controller.recommend, "method": "POST", "params": [ "username", "timestamp", "signature", "guid", "receivers" ] } }

## The WSGI callback function.
#  @param env WSGI environment
#  @param start_response function to start response
#  @return response text
def index(env, start_response):
	def validate_parameters(required, available):
		for p in required:
			if not p in available:
				return False

		return True

	global application
	global routing

	data = None
	form = None

	status = "200"
	response = ""
	content_type = "text/plain"
	view = None

	try:
		# try to map path to controller:
		handler = routing.get(env["PATH_INFO"], None)

		if handler is None:
			raise exception.HttpException(404, "Not Found")

		# validate method:
		if env["REQUEST_METHOD"] != handler["method"]:
			raise exception.HttpException(405, "Method Not Allowed")

		# get received parameters:
		if handler["method"] == "POST":
			# validate response length:
			if not env.has_key("CONTENT_LENGTH"):
				raise exception.HttpException(411, "Length Required")

			request_length = int(env["CONTENT_LENGTH"])

			if request_length > config.WSGI_MAX_REQUEST_LENGTH:
				raise exception.HttpException(413, "Request Entity Too Large")

			# get data from post request:
			if handler.get("multipart", False):
				form = FieldStorage(fp = env['wsgi.input'], environ = env)
			else:
				data = urlparse.parse_qs(env["wsgi.input"].read(request_length).decode(), True)
		else:
			data = urlparse.parse_qs(env["QUERY_STRING"], True)

		# validate parameters:
		args = []
		args_append = args.append

		if data is None:
			# handle multipart:
			file_key = handler.get("file_param", None)

			if not validate_parameters(handler["params"], form.keys()):
				raise exception.HttpException(400, "Bad Request")

			for p in handler["params"]:
				if not file_key is None and p == file_key:
					args_append(form[p].file)
				else:
					args_append(form.getvalue(p))

		else:
			# handle x-www-form-urlencoded:
			if not validate_parameters(handler["params"], data):
				raise exception.HttpException(400, "Bad Request")

			for p in handler["params"]:
				if form is None:
					args_append(data[p][0])

		view = handler["controller"](application, env, *args)

	except exception.HttpException, ex:
		status = ex.http_status
		response = ex.message

	except exception.Exception, ex:
		status = 500
		response = ex.message

		logging.error(ex.message)
		logging.error(traceback.print_exc())

	except Exception, ex:
		status = 500
		response = str(ex)

		logging.error(str(ex))
		logging.error(traceback.print_exc())

	finally:
		try:
			if not view is None:
				status = view.status
				content_type = view.content_type
				response = view.render()

		except Exception, ex:
			logging.error(str(ex))
			logging.error(traceback.print_exc())

		start_response(str(status), [ ("Content-type", content_type), ("Content-length", len(response)) ])

		return [ response ]
