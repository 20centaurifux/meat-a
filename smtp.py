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
#  @file smtp.py
#  SMTP functionality.

## @package smtp
#  SMTP functionality.

from mailer import MTA
from email.mime.text import MIMEText
import smtplib, logging, traceback, logger

## MTA sending emails via SMTP.
class SMTP_MTA(MTA):
	## The constructor.
	#  @param host hostname of the SMTP server
	#  @param port port of the SMTP server
	#  @param ssl True to enable SSL
	#  @param address address of the sender
	#  @param username username of the SMTP user
	#  @param password password of the SMTP user
	def __init__(self, host, port, ssl, address, username, password):
		self.server, self.port, self.ssl, self.address, self.username, self.password = host, port, ssl, address, username, password
		self.__client = None
		self.__logger = logger.get_logger()

	def start_session(self):
		self.__logger.debug("Starting mailer session.")

		if self.ssl:
			self.__client = smtplib.SMTP_SSL()
		else:
			self.__client = smtplib.SMTP()

		self.__client.connect(self.server, self.port)
		self.__client.login(self.username, self.password)

	def send(self, subject, body, receiver):
		try:
			self.__logger.info("Sending mail '%s' to '%s'", subject, receiver)

			msg = MIMEText(body, 'plain', 'utf-8')

			msg['Subject'] = subject
			msg['From'] = self.address
			msg['To'] = receiver

			self.__client.sendmail(self.address, [ receiver ], msg.as_string())

			return True

		except Exception, ex:
			self.__logger.error(ex)
			self.__logger.error(traceback.print_exc())

		return False

	def end_session(self):
		self.__logger.debug("Stopping mailer session.")
		self.__client.quit()
