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
#  @file template.py
#  Classes used for building strings.

## @package template
#  Classes used for building strings.

import abc, os, config, Cheetah.Template

## Dictionary storing content of template files.
tpl_cache = {}

## Loads the content from a template file and stores it in the template cache. Returns the
#  cached content whenever possible.
#  @param filename filename of the template to load
#  @return content of the template file
def load_template_def(filename):
	global tpl_cache

	try:
		tpl = tpl_cache[filename]

	except KeyError:
		with open(os.path.join(config.TEMPLATE_DIR, filename), "rb") as f:
			tpl = f.read()

	return tpl

## Base class for templates. A template can be exported to a string which contains binded data.
class Template:
	## Binds data.
	#  @param kwargs data to bind
	@abc.abstractmethod
	def bind(self, **kwargs): return

	## Converts the template to a string.
	#  @return a string
	@abc.abstractmethod
	def render(self): return None

## A Template implementation using the Cheetah framework.
class CheetahTemplate(Template):
	## The constructor.
	#  @param tpl name of a Cheetah template file
	def __init__(self, tpl):
		self.__namespace = {}
		self.__def = None
		self.__tpl = tpl

	def bind(self, **kwargs):
		self.__namespace = kwargs

	def render(self):
		if self.__def is None:
			self.__def = load_template_def(self.__tpl)

		t = Cheetah.Template.Template(self.__def, searchList = [ self.__namespace ])

		return str(t)

## A Template implementation using the Cheeta framework. It renders body and subject of a mail.
class CheetahMailTemplate(Template):
	## The constructor.
	#  @param subject_tpl template file used to generate the subject
	#  @param body_tpl template file used to generate the body
	def __init__(self, subject_tpl, body_tpl):
		self.__namespace = {}
		self.__defs = None
		self.__subject_tpl = subject_tpl
		self.__body_tpl = body_tpl

	def bind(self, **kwargs):
		self.__namespace = kwargs

	## Converts subject and body template to a string.
	#  @return subject and body
	def render(self):
		if self.__defs is None:
			self.__defs = []
			self.__defs.append(load_template_def(self.__subject_tpl))
			self.__defs.append(load_template_def(self.__body_tpl))

		subject = Cheetah.Template.Template(self.__defs[0], searchList = [ self.__namespace ])
		body = Cheetah.Template.Template(self.__defs[1], searchList = [ self.__namespace ])

		return str(subject), str(body)

## A Template implementation used for sending account request codes.
class AccountRequestMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "account_request_subject.tpl", "account_request_body.tpl")

## A Template implementation used to welcome new users.
class AccountActivationMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "account_activation_subject.tpl", "account_activation_body.tpl")

## A Template implementation used to inform users that their account has been disabled.
class AccountDisabledMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "account_disabled_subject.tpl", "account_disabled_body.tpl")

## A Template implementation used for sending password request codes.
class RequestNewPasswordMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "password_request_subject.tpl", "password_request_body.tpl")

## A Template implementation used to send a new generated password to users.
class PasswordResetMail(CheetahMailTemplate):
	def __init__(self):
		CheetahMailTemplate.__init__(self, "password_reset_subject.tpl", "password_reset_body.tpl")

## Website to inform users that their account has been activated.
class AccountActivatedPage(CheetahTemplate):
	def __init__(self):
		CheetahTemplate.__init__(self, "account_activated_html.tpl")

## Website to display faliure messages.
class FailureMessagePage(CheetahTemplate):
	def __init__(self):
		CheetahTemplate.__init__(self, "failure_message_html.tpl")

## Website to inform users that their password has been reseted.
class PasswordResetPage(CheetahTemplate):
	def __init__(self):
		CheetahTemplate.__init__(self, "password_reset_html.tpl")
