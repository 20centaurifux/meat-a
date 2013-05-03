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

import exception, view, factory, template, config, json, atexit
from app import RequestData
from database import RequestDb
from util import to_bool

SUCCESS = exception.ErrorCode.SUCCESS

"""
	store request & mail database instances globally, both instances share the same connection:
"""
shared_client = None
request_db = None
mail_db = None

# factory method to create shared client:
def create_shared_client():
	global shared_client

	if shared_client is None:
		shared_client = factory.create_shared_client()

	return shared_client

def close_shared_client():
	if not shared_client is None:
		shared_client.disconnect()

# register exit function to close shared client:
atexit.register(close_shared_client)

"""
	helper functions to create mails, HTML pages & count requests:
"""
def generate_mail(m, email, lifetime, **kwargs):
	global mail_db 

	m.bind(**kwargs)
	subject, body = m.render()

	if mail_db is None:
		mail_db = factory.create_shared_mail_db(create_shared_client())

	mail_db.append_message(subject, body, email, lifetime)

def generate_html(t, **kwargs):
	v = view.View("text/html", 200)
	t.bind(**kwargs)
	v.bind(t.render())

	return v

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
def request_account(app, env, username, email):
	v = view.JSONView(200)

	try:
		count_requests(env, RequestDb.RequestType.ACCOUNT_REQUEST, config.ACCOUNT_REQUESTS_PER_HOUR)

		code = app.request_account(username, email)
		generate_mail(template.AccountRequestMail(), email, config.USER_REQUEST_TIMEOUT, username = username, url = "%s/account/activate?code=%s" % (config.WEBSITE_URL, code))
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.InvalidParameterException, ex:
		v.bind({ "status": ex.code, "message": "Invalid parameter: '%s'" % ex.parameter })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })

	return v

def activate_account(app, env, code):
	try:
		count_requests(env, RequestDb.RequestType.ACCOUNT_REQUEST, config.ACCOUNT_REQUESTS_PER_HOUR)

		username, email, password = app.activate_user(code)
		generate_mail(template.AccountActivationMail(), email, config.USER_REQUEST_TIMEOUT, username = username, password = password)

		return generate_html(template.AccountActivatedPage(), username = username)

	except exception.Exception, ex:
		return generate_html(template.FailureMessagePage(), message = ex.message)

def disable_account(app, env, username, timestamp, signature, email):
	v = view.JSONView(200)

	try:
		app.disable_user(RequestData(username, int(timestamp), signature), email)
		generate_mail(template.AccountDisabledMail(), email, config.DEFAULT_EMAIL_LIFETIME, username = username)
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })

	return v

def update_password(app,env, username, timestamp, signature, old_password, new_password):
	return default_controller(app.change_password, env, (username, timestamp, signature, old_password, new_password))

def request_password(app, env, username, email):
	v = view.JSONView(200)

	try:
		count_requests(env, RequestDb.RequestType.PASSWORD_RESET, config.PASSWORD_RESETS_PER_HOUR)

		code = app.request_password(username, email)
		generate_mail(template.RequestNewPasswordMail(), email, config.PASSWORD_RESET_TIMEOUT,
		              username = username, url = "%s/account/password/reset?code=%s" % (config.WEBSITE_URL, code))
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })
		
	return v

def password_reset(app, env, code):
	try:
		count_requests(env, RequestDb.RequestType.PASSWORD_RESET, config.PASSWORD_RESETS_PER_HOUR)

		username, email, password = app.generate_password(code)
		generate_mail(template.PasswordResetMail(), email, config.DEFAULT_EMAIL_LIFETIME, username = username, password = password)

		return generate_html(template.PasswordResetPage(), username = username)

	except exception.Exception, ex:
		return generate_html(template.FailureMessagePage(), message = ex.message)
		
def update_user_details(app, env, username, timestamp, signature, email, firstname, lastname, gender, language, protected):
	return default_controller(app.update_user_details, env, (username, timestamp, signature, email, firstname, lastname, gender, language, to_bool(protected)))

def update_avatar(app, env, username, timestamp, signature, filename, stream):
	return default_controller(app.update_avatar, env, (username, timestamp, signature, filename, stream))

def search_user(app, env, username, timestamp, signature, query):
	return default_controller(app.find_user, env, (username, timestamp, signature, query), return_result = True)

def get_user_details(app, env, username, timestamp, signature, user):
	return default_controller(app.get_user_details, env, (username, timestamp, signature, user), return_result = True)

def get_object(app, env, username, timestamp, signature, guid):
	return default_controller(app.get_object, env, (username, timestamp, signature, guid), return_result = True)

def get_objects(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_objects, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def get_tagged_objects(app, env, username, timestamp, signature, tag, page, page_size):
	return default_controller(app.get_tagged_objects, env, (username, timestamp, signature, tag, int(page), int(page_size)), return_result = True, to_array = True)

def get_popular_objects(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_popular_objects, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def get_random_objects(app, env, username, timestamp, signature, page_size):
	return default_controller(app.get_random_objects, env, (username, timestamp, signature, int(page_size)), return_result = True)

def add_tags(app, env, username, timestamp, signature, guid, tags):
	return default_controller(app.add_tags, env, (username, timestamp, signature, guid, json.loads("[%s]" % tags)))

def rate(app, env, username, timestamp, signature, guid, up = True):
	return default_controller(app.rate, env, (username, timestamp, signature, guid, to_bool(up)))

def favor(app, env, username, timestamp, signature, guid, favor = True):
	return default_controller(app.favor, env, (username, timestamp, signature, guid, favor))

def get_favorites(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_favorites, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def add_comment(app, env, username, timestamp, signature, guid, text):
	return default_controller(app.add_comment, env, (username, timestamp, signature, guid, text))

def get_comments(app, env, username, timestamp, signature, guid, page, page_size):
	return default_controller(app.get_comments, env, (username, timestamp, signature, guid, int(page), int(page_size)), return_result = True, to_array = True)

def recommend(app, env, username, timestamp, signature, guid, receivers):
	return default_controller(app.recommend, env, (username, timestamp, signature, guid, json.loads("[%s]" % receivers)))

def get_recommendations(app, env, username, timestamp, signature, page, page_size):
	return default_controller(app.get_recommendations, env, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def follow(app, env, username, timestamp, signature, user, follow):
	return default_controller(app.follow, env, (username, timestamp, signature, user, to_bool(follow)))

def get_messages(app, env, username, timestamp, signature, limit, older_than):
	if older_than == "null":
		older_than = None
	else:
		older_than = int(older_than)

	return default_controller(app.get_messages, env, (username, timestamp, signature, int(limit), older_than), return_result = True, to_array = True)

def default_controller(f, env, args, return_result = False, to_array = False):
	v = view.JSONView(200)

	try:
		count_requests(env, RequestDb.RequestType.DEFAULT_REQUEST, config.REQUESTS_PER_HOUR)

		result = f(RequestData(args[0], int(args[1]), args[2]), *args[3:])

		if return_result:
			if to_array:
				v.bind([ r for r in result ])
			else:
				v.bind(result)
		else:
			v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.InvalidParameterException, ex:
		v.bind({ "status": ex.code, "message": "Invalid parameter: '%s'" % ex.parameter })

	except exception.Exception, ex:
		v = view.JSONView(200)
		v.bind({ "status": ex.code, "message": ex.message })

	return v
