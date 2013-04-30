# -*- coding: utf-8 -*-

import abc, os, config, Cheetah.Template

tpl_cache = {}

def load_template_def(filename):
	global tpl_cache

	try:
		tpl = tpl_cache[filename]

	except KeyError:
		with open(os.path.join(config.TEMPLATE_DIR, filename), "rb") as f:
			tpl = f.read()

	return tpl

class Template:
	@abc.abstractmethod
	def bind(self): return

	@abc.abstractmethod
	def render(self): return None

class CheetahTemplate(Template):
	def __init__(self, tpl):
		self.__namespace = {}
		self.__def = None
		self.__tpl = tpl

	def bind(self, **kwargs):
		self.__namespace = kwargs
		self.__def = None

	def render(self):
		if self.__def is None:
			self.__def = load_template_def(self.__tpl)

		t = Cheetah.Template.Template(self.__def, searchList = [ self.__namespace ])

		return str(t)

class CheetahMailTemplate(Template):
	def __init__(self, subject_tpl, body_tpl):
		self.__namespace = {}
		self.__defs = None
		self.__subject_tpl = subject_tpl
		self.__body_tpl = body_tpl

	def bind(self, **kwargs):
		self.__namespace = kwargs
		self.__defs = None

	def render(self):
		if self.__defs is None:
			self.__defs = []
			self.__defs.append(load_template_def(self.__subject_tpl))
			self.__defs.append(load_template_def(self.__body_tpl))

		subject = Cheetah.Template.Template(self.__defs[0], searchList = [ self.__namespace ])
		body = Cheetah.Template.Template(self.__defs[1], searchList = [ self.__namespace ])

		return str(subject), str(body)

class AccountRequestMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "account_request_subject.tpl", "account_request_body.tpl")

class AccountActivationMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "account_activation_subject.tpl", "account_activation_body.tpl")

class AccountDisabledMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "account_disabled_subject.tpl", "account_disabled_body.tpl")

class RequestNewPasswordMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "password_request_subject.tpl", "password_request_body.tpl")

class PasswordResetMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "password_reset_subject.tpl", "password_reset_body.tpl")

class AccountActivatedPage(CheetahTemplate):
	def __init__(self):
		CheetahTemplate.__init__(self, "account_activated_html.tpl")

class FailureMessagePage(CheetahTemplate):
	def __init__(self):
		CheetahTemplate.__init__(self, "failure_message_html.tpl")

class PasswordResetPage(CheetahTemplate):
	def __init__(self):
		CheetahTemplate.__init__(self, "password_reset_html.tpl")
