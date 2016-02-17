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
#  <p>Objects are stored in the object database (database.ObjectDb). They are
#  referenced by their guid and have a source. You can e.g. store a link
#  or a filename.
#
#  <p>Users can tag and rate objects. They can also add objects to their
#  personal favorite list and recommend them to other users. It's possible
#  to write comments too.</p>
#
#  <p>Users can follow each other. If user A follows user B and user B also
#  follows user A they are friends. Friends can recommend objects to each
#  other. If a user profile is not protected every user can recommend objects
#  to the user.</p>
#
#  <p>Users are organized in a separate user store (database.UserDb).</p>
#
#  <p>Several activities generate notifications. If a user adds an object to
#  his/her favorite  list friends will receive a notification for example. If the
#  user profile is not protected every user following the account will get a
#  notification. Like other items notifications are stored in separate data store
#  (database.StreamDb).</p>
#
#  <p>Sometimes a user will receive an email. If you're going to create a new user
#  profile a request code will be sent by email for example. Emails are stored
#  in the database.MailDb data store.</p>
#
#  <p>A service (mailer.Mailer) sends emails in a user-defined interval. This
#  process can also be triggered via an UDP request.</p>
#
#  <p>The different data stores can be accessed through the app.Application class.
#  The app.AuthenticatedApplication wraps the methods of this class and tests
#  additionally if a request is authenticated.</p>
#
#  <p>The authentication mechanism is quite simple. A request must contain at
#  least the username of a valid account and the current UNIX timestamp (UTC).
#  All parameters need to be sorted alphabetically. Then the HMAC-SHA1 checksum
#  has to be calculated. The required secret is the SHA-256 checksum of the
#  user password. You can find an example here: util.sign_message()</p>
#
#  <p>There's also a full example client available in the client module:
#  client.Client</p>
#
#  <p>The wsgi module tries to map a received path to a controller function.
#  Each controller returns a view.View object which will be used to generate
#  the response. The controller functions use an app.AuthenticatedApplication
#  instance to access the different data stores.</p>
#
#  <p>Data is stored with a MongoDB server but it's simple to use a different
#  backend.</p>
#
#  <p>To test the available modules execute the test.py file.</p>
#
#  <p>To configure the service please have a look at the config module.</p>
#
#  <p>You need the following additional packages to run the web interface:
#    <ul>
#      <li>PIL</li>
#      <li>Cheetah</li>
#      <li>pymongo</li>
#      <li>Rocket (optional)</li>
#    </ul>
#  </p>
#
#  <p>Have fun!</p>

import controller, re, urlparse, urllib
from app import Application

## An app.AuthenticatedApplication instance.
application = Application()

## Dictionary defining urls, their related controllers, required parameters & the allowed request methods ("POST" or "GET").
routing = [{"path": re.compile("^/user/registration$"), "controller": controller.AccountRequest},
           {"path": re.compile("^/user/registration/(?P<id>[^/]+)$"), "controller": controller.AccountActivation},
           {"path": re.compile("^/user/(?P<username>[^/]+)$"), "controller": controller.UserAccount},
           {"path": re.compile("^/user/(?P<username>[^/]+)/password/change$"), "controller": controller.PasswordRequest},
           {"path": re.compile("^/user/(?P<username>[^/]+)/password/change/(?P<id>[^/]+)$"), "controller": controller.PasswordChange},
           {"path": re.compile("^/user/(?P<username>[^/]+)/password$"), "controller": controller.UserPassword},
           {"path": re.compile("^/user/search/(?P<query>[^/]+)$"), "controller": controller.Search},
           {"path": re.compile("^/user/(?P<username>[^/]+)/friendship$"), "controller": controller.Friendship},
           {"path": re.compile("^/favorites$"), "controller": controller.Favorites},
           {"path": re.compile("^/messages$"), "controller": controller.Messages},
           {"path": re.compile("^/public/messages$"), "controller": controller.PublicMessages},
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
           {"path": re.compile("^/recommendations$"), "controller": controller.Recommendations}
           {"path": re.compile("^/recommendations/page/(?P<page>[\d+])$"), "controller": controller.Recommendations}
	   ]

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

		print v.status
		print v.headers
		print v.render()

	except StopIteration:
		# TODO: 404
		print "404"

from base64 import b64encode

env = {}
env["Authorization"] = "Basic %s" % b64encode(b"fnord:MegaFnord667").decode("ascii")
env["PATH_INFO"] = "/object/914423EC-D585-11E5-BEDF-50D719563991/abuse"
#env["QUERY_STRING"] = "text=fuck\nyou\nand\ndie"
env["REQUEST_METHOD"] = "put"

index(env, None)
