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
#  meat-a is a WSGI based webservice for the organization of objects and
#  related meta data.

import controller, re, urlparse, urllib, sys, httpcode, config, exception
from cgi import FieldStorage
from app import Application

## An app.AuthenticatedApplication instance.
application = Application()

## Default form handler. It receives parameters from the query string and body, when
#  the Content-Type is application/x-www-form-urlencoded.
#  @param env WSGI environment
def default_form_handler(method, env):
	qs = urlparse.parse_qs(env.get("QUERY_STRING", ""))
	params = {k: urllib.unquote(v[0]) for k, v in qs.items()}

	size = int(env.get('CONTENT_LENGTH', 0))

	if method in ["POST", "PUT"]:
		content_type = env.get("CONTENT_TYPE", "application/x-www-form-urlencoded")

		if content_type == "application/x-www-form-urlencoded":
			qs = urlparse.parse_qs(env['wsgi.input'].read(size))
			params.update({k: urllib.unquote(v[0]) for k, v in qs.items()})
		else:
			raise exception.HTTPException(400, "Bad Request: Content-Type not supported")

	return params

## Receive avatar from multipart form.
#  @param env WSGI environment
def avatar_form_handler(method, env):
	params = {}

	try:
		content_type = env.get("CONTENT_TYPE", "multipart/form-data")

		if not content_type.startswith("multipart/form-data"):
			raise exception.HTTPException(400, "Bad Request")

		form = FieldStorage(fp=env['wsgi.input'], environ=env)

		params["file"] = form["file"].file
		params["filename"] = form.getvalue("filename")

		return params

	except exception.HTTPException as e:
		raise e

	except Exception as e:
		raise exception.HTTPException(400, "Bad Request")

## Dictionary defining urls and their related controller.
routing = [{"path": re.compile("^/json/registration$"), "controller": controller.AccountRequest},
           {"path": re.compile("^/html/registration/(?P<id>[^/]+)$"), "controller": controller.AccountActivation},
           {"path": re.compile("^/html/registration/(?P<id>[^/]+)$"), "controller": controller.AccountActivation},
           {"path": re.compile("^/json/user/(?P<username>[^/]+)$"), "controller": controller.UserAccount},
           {"path": re.compile("^/json/user/(?P<username>[^/]+)/password/reset$"), "controller": controller.PasswordRequest},
           {"path": re.compile("^/html/user/(?P<username>[^/]+)/password/reset/(?P<id>[^/]+)$"), "controller": controller.PasswordChange},
           {"path": re.compile("^/json/user/(?P<username>[^/]+)/password$"), "controller": controller.UserPassword},
           {"path": re.compile("^/json/user/search/(?P<query>[^/]+)$"), "controller": controller.Search},
           {"path": re.compile("^/json/user/(?P<username>[^/]+)/friendship$"), "controller": controller.Friendship},
	   {"path": re.compile("^/json/user/(?P<username>[^/]+)/avatar$"), "controller": controller.Avatar, "form-handler": {"POST": avatar_form_handler}},
           {"path": re.compile("^/json/favorites$"), "controller": controller.Favorites},
           {"path": re.compile("^/json/messages$"), "controller": controller.Messages},
           {"path": re.compile("^/json/public$"), "controller": controller.PublicMessages},
           {"path": re.compile("^/json/object/(?P<guid>[^/]+)$"), "controller": controller.Object},
           {"path": re.compile("^/json/object/(?P<guid>[^/]+)/tags$"), "controller": controller.ObjectTags},
           {"path": re.compile("^/json/object/(?P<guid>[^/]+)/vote$"), "controller": controller.Voting},
           {"path": re.compile("^/json/object/(?P<guid>[^/]+)/comments$"), "controller": controller.Comments},
           {"path": re.compile("^/json/object/(?P<guid>[^/]+)/comments/page/((?P<page>[\d]+))$"), "controller": controller.Comments},
           {"path": re.compile("^/json/object/(?P<guid>[^/]+)/abuse$"), "controller": controller.ReportAbuse},
           {"path": re.compile("^/json/comment/(?P<id>[\d]+)$"), "controller": controller.Comment},
           {"path": re.compile("^/json/object/(?P<guid>[^/]+)/recommend$"), "controller": controller.Recommendations},
           {"path": re.compile("^/json/objects$"), "controller": controller.Objects},
           {"path": re.compile("^/json/objects/page/(?P<page>[\d]+)$"), "controller": controller.Objects},
           {"path": re.compile("^/json/objects/tag/(?P<tag>[^/]+)/page/(?P<page>[\d]+)$"), "controller": controller.TaggedObjects},
           {"path": re.compile("^/json/objects/tag/(?P<tag>[^/]+)$"), "controller": controller.TaggedObjects},
           {"path": re.compile("^/json/objects/tags$"), "controller": controller.TagCloud},
           {"path": re.compile("^/json/objects/popular/page/(?P<page>[\d]+)$"), "controller": controller.PopularObjects},
           {"path": re.compile("^/json/objects/popular$"), "controller": controller.PopularObjects},
           {"path": re.compile("^/json/objects/random$"), "controller": controller.RandomObjects},
           {"path": re.compile("^/json/recommendations$"), "controller": controller.Recommendations},
           {"path": re.compile("^/json/recommendations/page/(?P<page>[\d+])$"), "controller": controller.Recommendations}]

## The WSGI callback function.
#  @param env WSGI environment
#  @param start_response function to start response
#  @return response body
def index(env, start_response):
	global application
	global routing

	url = env["PATH_INFO"]
	parameters = {}
	controller = None

	try:
		# find route:
		f = lambda route: [route, route["path"].match(url)]
		route, m = next(pair for pair in map(f, routing) if pair[1] is not None)

		# test request length:
		size = int(env.get('CONTENT_LENGTH', 0))

		if size > config.WSGI_MAX_REQUEST_LENGTH:
			raise exception.StreamExceedsMaximumException()

		# get & run form handler:
		method = env["REQUEST_METHOD"].upper()

		try:
			handler = route["form-handler"].get(method, default_form_handler)

		except KeyError:
			handler = default_form_handler

		params = handler(method, env)

		# merge found parameters with parameters specified in path:
		params.update({k: urllib.unquote(m.group(k)) for k, v in route["path"].groupindex.items()})

		# execute controller:
		c = route["controller"]()
		v = c.handle_request(method, env, **params)

		status, headers = v.status, v.headers
		response = v.render()

	except StopIteration:
		status, headers = 404, {"Content-Type": "text/plain"}
		response = "Not Found"

	except exception.BaseException as e:
		status, headers = e.http_status, {"Content-Type": "text/plain"}
		response = e.message

	except:
		status, headers = 500, {"Content-Type", "text/plain"}
		response = sys.exc_info()[1]

	# add content length header, start response & return body:
	headers["Content-Length"] = str(len(response))

	start_response("%d %s" % (status, httpcode.codes[status][0]), headers.items())

	return response
