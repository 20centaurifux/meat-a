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

import abc, socket, threading, logging, traceback, factory, config

class MTA():
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def start_session(self): return

	@abc.abstractmethod
	def send(self, subject, body, receiver): return False

	@abc.abstractmethod
	def end_session(self): return

class Mailer:
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

	def start(self):
		self.socket.bind((self.host, self.port))
		self.__set_running__(True)

		self.__udp_thread = threading.Thread(target = self.__network_handler__)
		self.__udp_thread.start()

		self.__consumer_thread = threading.Thread(target = self.__consumer__)
		self.__consumer_thread.start()

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
				mails = db.get_unsent_messages(1000)

				while len(mails) > 0 and self.is_running():
					try:
						self.__mta.start_session()

						i = 0

						while i < len(mails) and self.is_running():
							m = mails[i]
							i += 1

							if self.__mta.send(["subject"], m["body"], m["receiver"]):
								db.mark_sent(m["id"])

						self.__mta.end_session()

					except Exception, ex:
						logging.error(ex.message)
						logging.error(traceback.print_exc())

					mails = db.get_unsent_messages(1000)

	def __notify__(self):
		self.__consumer_cond.acquire()
		self.__consumer_cond.notify()
		self.__consumer_cond.release()

def ping(host, port):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.sendto("ping\n", (host, port))
	s.close()
