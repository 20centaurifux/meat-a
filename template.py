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
#  Classes used to build strings.

## @package template
#  Classes used to build strings.

import abc, os, config, Cheetah.Template

## Dictionary storing content of template files.
tpl_cache = {}

## Loads the content from a template file and stores it in the template cache. Returns the
#  cached content whenever possible.
#  @param language language of the template
#  @param filename filename of the template to load
#  @return content of the template file
def load_template_def(language, filename):
	global tpl_cache

	filename = os.path.join(config.TEMPLATE_DIR, language, filename)

	try:
		tpl = tpl_cache[filename]

	except KeyError:
		with open(filename) as f:
			tpl = f.read()

	return tpl

## Base class for templates. A template can be exported to a string which contains binded data.
class Template:
	## The constructor.
	#  @param language language of the template
	def __init__(self, language):
		## Language of the template.
		self.language = language

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
	#  @param language language of the template
	#  @param tpl name of a Cheetah template file
	def __init__(self, language, tpl):
		Template.__init__(self, language)
		self.__namespace = {}
		self.__def = None
		self.__tpl = tpl

	def bind(self, **kwargs):
		self.__namespace = kwargs

	def render(self):
		if self.__def is None:
			self.__def = load_template_def(self.language, self.__tpl)

		t = Cheetah.Template.Template(self.__def, searchList = [ self.__namespace ])

		return str(t)

## A Template implementation using the Cheetah framework. It renders body and subject of a mail.
class CheetahMailTemplate(Template):
	## The constructor.
	#  @param language language of the template
	#  @param subject_tpl template file used to generate the subject
	#  @param body_tpl template file used to generate the body
	def __init__(self, language, subject_tpl, body_tpl):
		Template.__init__(self, language)
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
			self.__defs.append(load_template_def(self.language, self.__subject_tpl))
			self.__defs.append(load_template_def(self.language, self.__body_tpl))

		subject = Cheetah.Template.Template(self.__defs[0], searchList = [ self.__namespace ])
		body = Cheetah.Template.Template(self.__defs[1], searchList = [ self.__namespace ])

		return str(subject).strip(), str(body).strip()

## A Template implementation used for sending account request id & codes.
class AccountRequestMail(CheetahMailTemplate):
	def __init__(self, language):
		CheetahMailTemplate.__init__(self, language, "account_request.subject.tpl", "account_request.body.tpl")

## Account activation page.
class AccountActivationPage(CheetahTemplate):
	def __init__(self, language):
		CheetahTemplate.__init__(self, language, "account_activation_page.tpl")

## A page displaying successful account activation details.
class AccountActivatedPage(CheetahTemplate):
	def __init__(self, language):
		CheetahTemplate.__init__(self, language, "account_activated_page.tpl")

## A simple HTML page showing a message.
class MessagePage(CheetahTemplate):
	def __init__(self, language):
		CheetahTemplate.__init__(self, language, "message_page.tpl")

## A Template implementation used to welcome new users.
class AccountActivatedMail(CheetahMailTemplate):
	def __init__(self, language):
		CheetahMailTemplate.__init__(self, language, "account_activated.subject.tpl", "account_activated.body.tpl")

## A Template implementation used to inform users that their account has been disabled.
class AccountDisabledMail(CheetahMailTemplate):
	def __init__(self, language, disabled):
		if disabled:
			subject = "account_disabled.subject.tpl"
			body = "account_disabled.body.tpl"
		else:
			subject = "account_enabled.subject.tpl"
			body = "account_enabled.body.tpl"

		CheetahMailTemplate.__init__(self, language, subject, body)

## A Template implementation used to inform users that their account has been deleted.
class AccountDeletedMail(CheetahMailTemplate):
	def __init__(self, language):
		CheetahMailTemplate.__init__(self, language, "account_deleted.subject.tpl", "account_deleted.body.tpl")

## A Template implementation used for sending password request codes.
class PasswordRequestedMail(CheetahMailTemplate):
	def __init__(self, language):
		CheetahMailTemplate.__init__(self, language, "password_requested.subject.tpl", "password_requested.body.tpl")

## Account activation page.
class ChangePasswordPage(CheetahTemplate):
	def __init__(self, language):
		CheetahTemplate.__init__(self, language, "password_change_page.tpl")

## A simple HTML page showing a changed password notification.
class PasswordChangedPage(CheetahTemplate):
	def __init__(self, language):
		CheetahTemplate.__init__(self, language, "password_changed_page.tpl")

## A Template implementation used to send a new generated password to users.
class PasswordChangedMail(CheetahMailTemplate):
	def __init__(self, language):
		CheetahMailTemplate.__init__(self, language, "password_changed.subject.tpl", "password_changed.body.tpl")
