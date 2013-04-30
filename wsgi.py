# -*- coding: utf-8 -*-

import urlparse, config, exception, controller, logging, traceback
from app import AuthenticatedApplication
from cgi import FieldStorage

application = AuthenticatedApplication()

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

		if data is None:
			# handle multipart:
			file_key = handler.get("file_param", None)

			if not validate_parameters(handler["params"], form.keys()):
				raise exception.HttpException(400, "Bad Request")

			for p in handler["params"]:
				if not file_key is None and p == file_key:
					args.append(form[p].file)
				else:
					args.append(form.getvalue(p))

		else:
			# handle x-www-form-urlencoded:
			if not validate_parameters(handler["params"], data):
				raise exception.HttpException(400, "Bad Request")

			for p in handler["params"]:
				if form is None:
					args.append(data[p][0])

		view = handler["controller"](application, *args)

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
