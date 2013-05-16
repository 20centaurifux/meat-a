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

import exception, view, factory, template, config, json, atexit
from app import RequestData
from database import RequestDb
from util import to_bool
from mailer import ping

## Code for succeeded operations.
SUCCESS = exception.ErrorCode.SUCCESS

"""
	store request & mail database instances globally, both instances share the same connection:
"""
## A shared database client instance. request_db and mail_db use this connection.
shared_client = None
## A database.RequestDb instance.
request_db = None
## A database.MailDb instance.
mail_db = None

## Initializes the shared database connection.
def create_shared_client():
	global shared_client

	if shared_client is None:
		shared_client = factory.create_shared_client()

	return shared_client

## Closes the shared database connection.
def close_shared_client():
	if not shared_client is None:
		shared_client.disconnect()

# register exit function to close shared client:
atexit.register(close_shared_client)

"""
	helper functions to create mails, HTML pages & count requests:
"""
## Generates a mail using the given template & stores it in the queue.
#  @param m a mail template
#  @param email email address of the receiver
#  @param lifetime lifetime in the queue
#  @param kwargs data used to fill the template
def generate_mail(m, email, lifetime, **kwargs):
	global mail_db 

	m.bind(**kwargs)
	subject, body = m.render()

	if mail_db is None:
		mail_db = factory.create_shared_mail_db(create_shared_client())

	mail_db.append_message(subject, body, email, lifetime)

## Generates an HTML response.
#  @param t template to use
#  @param kwargs data used to fill the template
#  @return the rendered template
def generate_html(t, **kwargs):
	v = view.View("text/html", 200)
	t.bind(**kwargs)
	v.bind(t.render())

	return v

## Tests if the HTTP request limit for an IP address has been reached.
#  @param env WSGI environment
#  @param code type of the request (see data.RequestDb.RequestType)
#  @param max_count maximum number of allowed requests
def count_requests(env, code, max_count):
	global request_db

	if not config.LIMIT_REQUESTS:
		return

	try:
		ip = env["HTTP_X_FORWARDED_FOR"].split(",")[-1].strip()

	except KeyError:
		ip = env["REMOTE_ADDR"]

	if request_db is None:
		request_db = factory.create_shared_request_db(create_shared_client())

	request_db.append_request(code, ip)
	count = request_db.count_requests(code, ip)

	if count > max_count:
		raise exception.TooManyRequestsException()

"""
	controller:
"""
## Tries to create a user request & sends an email on success.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username requested username
#  @param email email address of the account
#  @return a JSON view ('{ "status": int, "message": str }')
def request_account(app, env, username, email):
	v = view.JSONView(200)

	try:
		count_requests(env, RequestDb.RequestType.ACCOUNT_REQUEST, config.ACCOUNT_REQUESTS_PER_HOUR)

		code = app.request_account(username, email)
		generate_mail(template.AccountRequestMail(), email, config.USER_REQUEST_TIMEOUT, username = username, url = "%s/account/activate?code=%s" % (config.WEBSITE_URL, code))
		ping(config.MAILER_HOST, config.MAILER_PORT)
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.InvalidParameterException, ex:
		v.bind({ "status": ex.code, "message": "Invalid parameter: '%s'" % ex.parameter })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })

	return v

## Activates a user account using an existing request code. An email will be sent to the related
#  account on success.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param code a user request code
#  @return an HTML view
def activate_account(app, env, code):
	try:
		count_requests(env, RequestDb.RequestType.ACCOUNT_REQUEST, config.ACCOUNT_REQUESTS_PER_HOUR)

		username, email, password = app.activate_user(code)
		generate_mail(template.AccountActivationMail(), email, config.USER_REQUEST_TIMEOUT, username = username, password = password)
		ping(config.MAILER_HOST, config.MAILER_PORT)

		return generate_html(template.AccountActivatedPage(), username = username)

	except exception.Exception, ex:
		return generate_html(template.FailureMessagePage(), message = ex.message)

## Disable a user account.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param email email address of the account
#  @return a JSON view ('{ "status": int, "message": str }')
def disable_account(app, env, username, timestamp, signature, email):
	v = view.JSONView(200)

	try:
		app.disable_user(RequestData(username, int(timestamp), signature), email)
		generate_mail(template.AccountDisabledMail(), email, config.DEFAULT_EMAIL_LIFETIME, username = username)
		ping(config.MAILER_HOST, config.MAILER_PORT)
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })

	return v

## Changes the password of a user account.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param old_password old password of the user (plaintext)
#  @param new_password new password of the user (plaintext)
#  @return a JSON view ('{ "status": int, "message": str }')
def update_password(app,env, username, timestamp, signature, old_password, new_password):
	return default_controller(app.change_password, env, (username, timestamp, signature, old_password, new_password))

## Requests an auto-generated password. The request code will be sent by email.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of a user account
#  @param email email address of the user account
#  @return a JSON view ('{ "status": int, "message": str }')
def request_password(app, env, username, email):
	v = view.JSONView(200)

	try:
		count_requests(env, RequestDb.RequestType.PASSWORD_RESET, config.PASSWORD_RESETS_PER_HOUR)

		code = app.request_password(username, email)
		generate_mail(template.RequestNewPasswordMail(), email, config.PASSWORD_RESET_TIMEOUT,
		              username = username, url = "%s/account/password/reset?code=%s" % (config.WEBSITE_URL, code))
		ping(config.MAILER_HOST, config.MAILER_PORT)
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })
		
	return v

## Generate user password using a request code. The user receives the new password by email.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param code password reset code
#  @return an HTML view
def password_reset(app, env, code):
	try:
		count_requests(env, RequestDb.RequestType.PASSWORD_RESET, config.PASSWORD_RESETS_PER_HOUR)

		username, email, password = app.generate_password(code)
		generate_mail(template.PasswordResetMail(), email, config.DEFAULT_EMAIL_LIFETIME, username = username, password = password)
		ping(config.MAILER_HOST, config.MAILER_PORT)

		return generate_html(template.PasswordResetPage(), username = username)

	except exception.Exception, ex:
		return generate_html(template.FailureMessagePage(), message = ex.message)

## Updates user details.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param email email address to set
#  @param firstname firstname to set
#  @param lastname lastname to set
#  @param gender gender to set
#  @param language language to set
#  @param protected protected status to set
#  @return a JSON view ('{ "status": int, "message": str }')
def update_user_details(app, env, username, timestamp, signature, email, firstname, lastname, gender, language, protected):
	return default_controller(app.update_user_details, env, (username, timestamp, signature, email, firstname, lastname, gender, language, to_bool(protected)))

## Updates avatar of a user.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param filename filename of the avatar
#  @param stream input stream to read image data
#  @return a JSON view ('{ "status": int, "message": str }')
def update_avatar(app, env, username, timestamp, signature, filename, stream):
	return default_controller(app.update_avatar, env, (username, timestamp, signature, filename, stream))

## Searches the user data store.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param query a search query
#  @return a JSON view:  '[ { "name": str, "firstname": str, "lastname": str, "email": str,
#                             "gender": str, "timestamp": float, "avatar": str, "protected": bool,
#                             "following":  [ str, str, ... ] } ]';
#                        only friends can see the "email" and "following" fields
def search_user(app, env, username, timestamp, signature, query):
	return default_controller(app.find_user, env, (username, timestamp, signature, query), return_result = True)

## Gets details of a user account.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param user name of a user account
#  @return a JSON view: '[ { "name": str, "firstname": str, "lastname": str, "email": str,
#                            "gender": str, "timestamp": float, "avatar": str, "protected": bool, "following":  [ str, str, ... ] } ]';
#                       only friends can see the "email" and "following" fields
def get_user_details(app, env, username, timestamp, signature, user):
	return default_controller(app.get_user_details, env, (username, timestamp, signature, user), return_result = True)

## Gets object details.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param guid guid of an object
#  @return a JSON view: '{ "guid": str, "source": str, "locked": bool, "tags": [ str, str, ... ],
#                          "score": { "up": int, "down": int, "fav": int, "total": int },
#                          "timestamp": float, "comments_n": int }'
def get_object(app, env, username, timestamp, signature, guid):
	return default_controller(app.get_object, env, (username, timestamp, signature, guid), return_result = True)

## Gets objects from the data store.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param page page number
#  @param page_size size of each page
#  @return a JSON view: '[ { "guid": str, "source": str, "locked": bool, "tags": [ str, str, ... ],
#                            "score": { "up": int, "down": int, "fav": int, "total": int },
#                            "timestamp": float, "comments_n": int } ]'
def get_objects(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_objects, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True)

## Gets objects assigned to a tag.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param tag a tag
#  @param page page number
#  @param page_size size of each page
#  @return a JSON view: '[ { "guid": str, "source": str, "locked": bool, "tags": [ str, str, ... ],
#                            "score": { "up": int, "down": int, "fav": int, "total": int },
#                            "timestamp": float, "comments_n": int } ]'
def get_tagged_objects(app, env, username, timestamp, signature, tag, page, page_size):
	return default_controller(app.get_tagged_objects, env, (username, timestamp, signature, tag, int(page), int(page_size)), return_result = True)

## Gets the most popular objects.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param page page number
#  @param page_size size of each page
#  @return a JSON view: '[ { "guid": str, "source": str, "locked": bool, "tags": [ str, str, ... ],
#                            "score": { "up": int, "down": int, "fav": int, "total": int },
#                            "timestamp": float, "comments_n": int } ]'
def get_popular_objects(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_popular_objects, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True)

## Gets random objects.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param page_size the page size
#  @return a JSON view: '[ { "guid": str, "source": str, "locked": bool, "tags": [ str, str, ... ],
#                            "score": { "up": int, "down": int, "fav": int, "total": int },
#                            "timestamp": float, "comments_n": int } ]'
def get_random_objects(app, env, username, timestamp, signature, page_size): 
	return default_controller(app.get_random_objects, env, (username, timestamp, signature, int(page_size)), return_result = True)

## Adds tags to an object.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param guid guid of an object
#  @param tags tags stored in a JSON view (e.g. '[ "foo", "bar" ]')
#  @return a JSON view ('{ "status": int, "message": str }')
def add_tags(app, env, username, timestamp, signature, guid, tags):
	return default_controller(app.add_tags, env, (username, timestamp, signature, guid, json.loads("[%s]" % tags)))

## Upvotes/Downvotes an object.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param guid guid of an object
#  @param up True to upvote
#  @return a JSON view ('{ "status": int, "message": str }')
def rate(app, env, username, timestamp, signature, guid, up = True):
	return default_controller(app.rate, env, (username, timestamp, signature, guid, to_bool(up)))

## Adds an object to the favorites list of a user.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param guid guid of an object
#  @param favor True to add the object to the list
#  @return a JSON view ('{ "status": int, "message": str }')
def favor(app, env, username, timestamp, signature, guid, favor = True):
	return default_controller(app.favor, env, (username, timestamp, signature, guid, favor))

## Gets the favorites list of a user.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param page page number
#  @param page_size size of each page
#  @return a JSON view: '[ { "guid": str, "source": str, "locked": bool, "tags": [ str, str, ... ],
#                            "score": { "up": int, "down": int, "fav": int, "total": int },
#                            "timestamp": float, "comments_n": int } ]'
def get_favorites(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_favorites, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True)

## Appends a comment to an object.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param guid guid of an object
#  @param text text to append
#  @return a JSON view ('{ "status": int, "message": str }')
def add_comment(app, env, username, timestamp, signature, guid, text):
	return default_controller(app.add_comment, env, (username, timestamp, signature, guid, text))

## Gets comments assigned to an object.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param guid guid of an object
#  @param page page number
#  @param page_size size of each page
#  @return a JSON view: '[ { "text": str, "timestamp": float, "user": { "name": str, "firstname": str, "lastname": str,
#                            "gender": str, "avatar": str, "blocked": bool } ]'
def get_comments(app, env, username, timestamp, signature, guid, page, page_size):
	return default_controller(app.get_comments, env, (username, timestamp, signature, guid, int(page), int(page_size)), return_result = True)

## Lets a user recommend an object to his/her friends.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param guid guid of an object
#  @param receivers receivers stored in a JSON view (e.g. '[ "foo", "bar" ]')
#  @return a JSON view ('{ "status": int, "message": str }')
def recommend(app, env, username, timestamp, signature, guid, receivers):
	return default_controller(app.recommend, env, (username, timestamp, signature, guid, json.loads("[%s]" % receivers)))

## Gets objects recommended to a user.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param page page number
#  @param page_size size of each page
#  @return a JSON view: '[ { "guid": str, "source": str, "locked": bool, "tags": [ str, str, ... ],
#                            "score": { "up": int, "down": int, "fav": int, "total": int },
#                            "timestamp": float, "comments_n": int } ]'
def get_recommendations(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_recommendations, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True)

## Lets one user follow another user.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param user user to follow
#  @param follow True to follow the user
#  @return a JSON view ('{ "status": int, "message": str }')
def follow(app, env, username, timestamp, signature, user, follow):
	return default_controller(app.follow, env, (username, timestamp, signature, user, to_bool(follow)))

## Gets messages assigned to a user.
#  @param app app.AuthenticatedApplication instance
#  @param env WSGI environment
#  @param username name of the authenticated user
#  @param timestamp UNIX timestamp of the request (UTC)
#  @param signature checksum of the request parameters
#  @param limit number of messages to receive
#  @param older_than filter to get only messages older than the specified timestamp
#  @return a JSON view: '[ { "type_id": int, "timestamp": float, "sender": { "name": str, "firstname": str,
#                            "lastname": str, "gender": str, "avatar": str, "blocked": bool },
#                            [ optional fields depending on message type] } ]'
def get_messages(app, env, username, timestamp, signature, limit, older_than):
	if older_than == "null":
		older_than = None
	else:
		older_than = float(older_than)

	return default_controller(app.get_messages, env, (username, timestamp, signature, int(limit), older_than), return_result = True)

## Default controller function. The function executes a specified callback function and returns the result.
#  @param f callback function
#  @param env the WSGI environment
#  @param args arguments passed to the callback function
#  @param return_result if True the view.JSONView will hold the result of the given callback function
#  @return a view.JSONView instance
def default_controller(f, env, args, return_result = False):
	v = view.JSONView(200)

	try:
		count_requests(env, RequestDb.RequestType.DEFAULT_REQUEST, config.REQUESTS_PER_HOUR)

		result = f(RequestData(args[0], int(args[1]), args[2]), *args[3:])

		if return_result:
			v.bind(result)
		else:
			v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.InvalidParameterException, ex:
		v.bind({ "status": ex.code, "message": "Invalid parameter: '%s'" % ex.parameter })

	except exception.Exception, ex:
		v = view.JSONView(200)
		v.bind({ "status": ex.code, "message": ex.message })

	return v
