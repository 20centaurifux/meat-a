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
#  @file mailer.py
#  A service sending mails found in the mail queue. Mails will be sent after an interval.
#  This process can also be triggered by UDP.

## @package mailer
#  A service sending mails found in the mail queue. Mails will be sent after an interval.
#  This process can also be triggered by UDP.

import abc, socket, threading, logging, traceback, factory, config

## Base class for mail transfer agents.
class MTA():
	__metaclass__ = abc.ABCMeta

	## Called when the Mailer starts a new session.
	@abc.abstractmethod
	def start_session(self): return

	## Sends an mail to a receiver.
	#  @param subject subject of the mail
	#  @param body body of the mail
	#  @param receiver receiver of the mail
	#  @return if True the Mailer sets the "Sent" flag of the mail, otherwise it stays
	#          in the queue
	@abc.abstractmethod
	def send(self, subject, body, receiver): return False

	## Called when a Mailer session ends.
	@abc.abstractmethod
	def end_session(self): return

## A service sending mails from the mail queue using an assigned MTA. It sends mails after an
#  interval or when triggered over UDP.
class Mailer:
	## The constructor.
	#  @param host host where the service should listen
	#  @param port port of the service
	#  @param mta a MTA instance used to send mails
	def __init__(self, host, port, mta):
		self.host = host
		self.port = port

		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.setblocking(0)
		self.socket.settimeout(config.MAILER_UDP_TIMEOUT)

		self.__udp_thread = None
		self.__running = False
		self.__running_lock = threading.Lock()

		self.__consumer_thread = None
		self.__consumer_lock = threading.Lock()
		self.__consumer_cond = threading.Condition(self.__consumer_lock)

		self.__mta = mta

	## Starts the service.
	def start(self):
		self.socket.bind((self.host, self.port))
		self.__set_running__(True)

		self.__udp_thread = threading.Thread(target = self.__network_handler__)
		self.__udp_thread.start()

		self.__consumer_thread = threading.Thread(target = self.__consumer__)
		self.__consumer_thread.start()

	## Stops the service.
	def quit(self):
		# unset "running" flag:
		self.__set_running__(False)

		# wait for consumer:
		self.__notify__()
		self.__consumer_thread.join()

		# wait for network thread & close socket:
		self.__udp_thread.join()
		self.socket.close()
		self.socket= None

	## Tests if the service is running.
	#  @return True if the service is running
	def is_running(self):
		self.__running_lock.acquire()
		running = self.__running
		self.__running_lock.release()

		return running

	def __set_running__(self, running):
		self.__running_lock.acquire()
		self.__running = running
		self.__running_lock.release()

	def __network_handler__(self):
		while self.is_running():
			try:
				data, addr = self.socket.recvfrom(128) 

				if addr[0] in config.MAILER_ALLOWED_CLIENTS:
					if data == "ping\n":
						self.__notify__()

			except socket.timeout:
				pass

	def __consumer__(self):
		with factory.create_mail_db() as db:
			while True:
				self.__consumer_cond.acquire()
				self.__consumer_cond.wait(config.MAIL_CHECK_INTERVAL)
				self.__consumer_cond.release()

				if not self.is_running():
					break

				# get & send mails:
				mails = db.get_unsent_messages(100)

				if len(mails) > 0:
					try:
						self.__mta.start_session()

						for m in mails:
							if self.__mta.send(m["subject"], m["body"], m["receiver"]):
								db.mark_sent(m["id"])

							if not self.is_running():
								break

						self.__mta.end_session()

					except Exception, ex:
						print "ne"
						logging.error(ex.message)
						logging.error(traceback.print_exc())



	def __notify__(self):
		self.__consumer_cond.acquire()
		self.__consumer_cond.notify()
		self.__consumer_cond.release()

## Triggers the Mailer to send emails.
#  @param host host of the mailer
#  @param port port of the mailer
def ping(host, port):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.sendto("ping\n", (host, port))
	s.close()

if __name__ == "__main__":
	m = Mailer(config.MAILER_HOST, config.MAILER_PORT, factory.create_mta())
	m.start()

	print "[press enter to quit]"
	raw_input()

	print "Shutting down... please wait!"
	m.quit()
