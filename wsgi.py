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

import controller, re, urlparse, urllib, sys, httpcode
from app import Application

## An app.AuthenticatedApplication instance.
application = Application()

## Dictionary defining urls and their related controller.
routing = [{"path": re.compile("^/registration$"), "controller": controller.AccountRequest},
           {"path": re.compile("^/registration/(?P<id>[^/]+)$"), "controller": controller.AccountActivation},
           {"path": re.compile("^/user/(?P<username>[^/]+)$"), "controller": controller.UserAccount},
           {"path": re.compile("^/user/(?P<username>[^/]+)/password/reset$"), "controller": controller.PasswordRequest},
           {"path": re.compile("^/user/(?P<username>[^/]+)/password/reset/(?P<id>[^/]+)$"), "controller": controller.PasswordChange},
           {"path": re.compile("^/user/(?P<username>[^/]+)/password$"), "controller": controller.UserPassword},
           {"path": re.compile("^/user/search/(?P<query>[^/]+)$"), "controller": controller.Search},
           {"path": re.compile("^/user/(?P<username>[^/]+)/friendship$"), "controller": controller.Friendship},
           {"path": re.compile("^/favorites$"), "controller": controller.Favorites},
           {"path": re.compile("^/messages$"), "controller": controller.Messages},
           {"path": re.compile("^/public$"), "controller": controller.PublicMessages},
           {"path": re.compile("^/object/(?P<guid>[^/]+)$"), "controller": controller.Object},
           {"path": re.compile("^/object/(?P<guid>[^/]+)/tags$"), "controller": controller.ObjectTags},
           {"path": re.compile("^/object/(?P<guid>[^/]+)/vote$"), "controller": controller.Voting},
           {"path": re.compile("^/object/(?P<guid>[^/]+)/comments$"), "controller": controller.Comments},
           {"path": re.compile("^/object/(?P<guid>[^/]+)/comments/page/((?P<page>[\d]+))$"), "controller": controller.Comments},
           {"path": re.compile("^/object/(?P<guid>[^/]+)/abuse$"), "controller": controller.ReportAbuse},
           {"path": re.compile("^/comment/(?P<id>[\d]+)$"), "controller": controller.Comment},
           {"path": re.compile("^/object/(?P<guid>[^/]+)/recommend$"), "controller": controller.Recommendations},
           {"path": re.compile("^/objects$"), "controller": controller.Objects},
           {"path": re.compile("^/objects/page/(?P<page>[\d]+)$"), "controller": controller.Objects},
           {"path": re.compile("^/objects/tag/(?P<tag>[^/]+)/page/(?P<page>[\d]+)$"), "controller": controller.TaggedObjects},
           {"path": re.compile("^/objects/tag/(?P<tag>[^/]+)$"), "controller": controller.TaggedObjects},
           {"path": re.compile("^/objects/tags$"), "controller": controller.TagCloud},
           {"path": re.compile("^/objects/popular/page/(?P<page>[\d]+)$"), "controller": controller.PopularObjects},
           {"path": re.compile("^/objects/popular$"), "controller": controller.PopularObjects},
           {"path": re.compile("^/objects/random$"), "controller": controller.RandomObjects},
           {"path": re.compile("^/recommendations$"), "controller": controller.Recommendations},
           {"path": re.compile("^/recommendations/page/(?P<page>[\d+])$"), "controller": controller.Recommendations}]

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

		# get parameters from query string:
		try:
			size = int(env.get('CONTENT_LENGTH', 0))
			# TODO check length
			qs = env['wsgi.input'].read(size)

		except KeyError:
			qs = env.get("QUERY_STRING", "")

 		qs = urlparse.parse_qs(qs, True)

		params = {k: urllib.unquote(v[0]) for k, v in qs.items()}

		# merge found parameters with parameters specified in path:
		params.update({k: urllib.unquote(m.group(k)) for k, v in route["path"].groupindex.items()})

		# execute controller:
		c = route["controller"]()
		v = c.handle_request(env["REQUEST_METHOD"], env, **params)

		status, headers = v.status, v.headers
		response = v.render()

	except StopIteration:
		status, headers = 404, {"Content-Type": "text/plain"}
		response = "Not Found"

	except:
		status, headers = 500, {"Content-Type", "text/plain"}
		response = sys.exc_info()[1]

	# add content length header, start response & return body:
	headers["Content-Length"] = str(len(response))

	start_response("%d %s" % (status, httpcode.codes[status][0]), headers.items())

	return [response]
