# -*- coding: utf-8 -*-

import exception, view, factory, template, config, json
from app import RequestData
from util import to_bool

SUCCESS = exception.ErrorCode.SUCCESS

def generate_mail(m, email, lifetime, **kwargs):
	m.bind(**kwargs)
	subject, body = m.render()

	with factory.create_mail_db() as db:
		db.append_message(subject, body, email, lifetime)

def generate_html(t, **kwargs):
	v = view.View("text/html", 200)
	t.bind(**kwargs)
	v.bind(t.render())

	return v

def request_account(app, username, email):
	v = view.JSONView(200)

	try:
		code = app.request_account(username, email)
		generate_mail(template.AccountRequestMail(), email, config.USER_REQUEST_TIMEOUT, username = username, url = "%s/account/activate?code=%s" % (config.WEBSITE_URL, code))
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.InvalidParameterException, ex:
		v.bind({ "status": ex.code, "message": "Invalid parameter: '%s'" % ex.parameter })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })

	return v

def activate_account(app, code):
	try:
		username, email, password = app.activate_user(code)
		generate_mail(template.AccountActivationMail(), email, config.USER_REQUEST_TIMEOUT, username = username, password = password)

		return generate_html(template.AccountActivatedPage(), username = username)

	except exception.Exception, ex:
		return generate_html(template.FailureMessagePage(), message = ex.message)

def disable_account(app, username, timestamp, signature, email):
	v = view.JSONView(200)

	try:
		app.disable_user(RequestData(username, int(timestamp), signature), email)
		generate_mail(template.AccountDisabledMail(), email, config.DEFAULT_EMAIL_LIFETIME, username = username)
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })

	return v

def update_password(app, username, timestamp, signature, old_password, new_password):
	return default_controller(app.change_password, (username, timestamp, signature, old_password, new_password))

def request_password(app, username, email):
	v = view.JSONView(200)

	try:
		code = app.request_password(username, email)
		generate_mail(template.RequestNewPasswordMail(), email, config.PASSWORD_RESET_TIMEOUT,
		              username = username, url = "%s/account/password/reset?code=%s" % (config.WEBSITE_URL, code))
		v.bind({ "status": SUCCESS, "message": "ok" })

	except exception.Exception, ex:
		v.bind({ "status": ex.code, "message": ex.message })
		
	return v

def password_reset(app, code):
	try:
		username, email, password = app.generate_password(code)
		generate_mail(template.PasswordResetMail(), email, config.DEFAULT_EMAIL_LIFETIME, username = username, password = password)

		return generate_html(template.PasswordResetPage(), username = username)

	except exception.Exception, ex:
		return generate_html(template.FailureMessagePage(), message = ex.message)
		
def update_user_details(app, username, timestamp, signature, email, firstname, lastname, gender, language, protected):
	return default_controller(app.update_user_details, (username, timestamp, signature, email, firstname, lastname, gender, language, to_bool(protected)))

def update_avatar(app, username, timestamp, signature, filename, stream):
	return default_controller(app.update_avatar, (username, timestamp, signature, filename, stream))

def search_user(app, username, timestamp, signature, query):
	return default_controller(app.find_user, (username, timestamp, signature, query), return_result = True)

def get_user_details(app, username, timestamp, signature, user):
	return default_controller(app.get_user_details, (username, timestamp, signature, user), return_result = True)

def get_object(app, username, timestamp, signature, guid):
	return default_controller(app.get_object, (username, timestamp, signature, guid), return_result = True)

def get_objects(app, username, timestamp, signature, page, page_size):
	return default_controller(app.get_objects, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def get_tagged_objects(app, username, timestamp, signature, tag, page, page_size):
	return default_controller(app.get_tagged_objects, (username, timestamp, signature, tag, int(page), int(page_size)), return_result = True, to_array = True)

def get_popular_objects(app, username, timestamp, signature, page, page_size):
	return default_controller(app.get_popular_objects, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def get_random_objects(app, username, timestamp, signature, page_size):
	return default_controller(app.get_random_objects, (username, timestamp, signature, int(page_size)), return_result = True)

def add_tags(app, username, timestamp, signature, guid, tags):
	return default_controller(app.add_tags, (username, timestamp, signature, guid, json.loads("[%s]" % tags)))

def rate(app, username, timestamp, signature, guid, up = True):
	return default_controller(app.rate, (username, timestamp, signature, guid, to_bool(up)))

def favor(app, username, timestamp, signature, guid, favor = True):
	return default_controller(app.favor, (username, timestamp, signature, guid, favor))

def get_favorites(app, username, timestamp, signature, page, page_size):
	return default_controller(app.get_favorites, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def add_comment(app, username, timestamp, signature, guid, text):
	return default_controller(app.add_comment, (username, timestamp, signature, guid, text))

def get_comments(app, username, timestamp, signature, guid, page, page_size):
	return default_controller(app.get_comments, (username, timestamp, signature, guid, int(page), int(page_size)), return_result = True, to_array = True)

def recommend(app, username, timestamp, signature, guid, receivers):
	return default_controller(app.recommend, (username, timestamp, signature, guid, json.loads("[%s]" % receivers)))

def get_recommendations(app, username, timestamp, signature, page, page_size):
	return default_controller(app.get_recommendations, (username, timestamp, signature, int(page), int(page_size)), return_result = True, to_array = True)

def follow(app, username, timestamp, signature, user, follow):
	return default_controller(app.follow, (username, timestamp, signature, user, to_bool(follow)))

def get_messages(app, username, timestamp, signature, limit, older_than):
	if older_than == "null":
		older_than = None
	else:
		older_than = int(older_than)

	return default_controller(app.get_messages, (username, timestamp, signature, int(limit), older_than), return_result = True, to_array = True)

def default_controller(f, args, return_result = False, to_array = False):
	v = view.JSONView(200)

	try:
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
