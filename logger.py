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
#  @file logger.py
#  A logging.Logger wrapper.

## @package logger
#  A logging.Logger wrapper.

import config, logging

logger = None

## A logging.Logger wrapper.
class LoggerWrapper():
	## The constructor.
	#  @param logger a logging.Logger instance to wrap
	#  @param request_id optional request id
	def __init__(self, logger, request_id=None):
		self.__logger = logger
		self.__request_id = request_id

		self.debug = self.__log_func__(logging.DEBUG)
		self.info = self.__log_func__(logging.INFO)
		self.warning = self.__log_func__(logging.WARNING)
		self.error = self.__log_func__(logging.ERROR)
		self.critical = self.__log_func__(logging.CRITICAL)

	def log(self, level, msg, *args):
		if self.__request_id is None:
			self.__logger.log(level, msg, *args)
		else:
			self.__logger.log(level, "%s => %s", self.__request_id, msg % args)

	def __log_func__(self, level):
		return lambda msg, *args: self.log(level, msg, *args)

## Creates the default logger.
#  @param request_id optional request id
#  @return a LoggerWrapper instance
def get_logger(request_id=None):
	global logger

	if logger is None:
		logger = logging.Logger(config.LOGGING_NAME)
		logger.setLevel(config.LOGGING_VERBOSITY)

		handler = config.LOGGING_HANDLER()
		handler.setFormatter(logging.Formatter(config.LOGGING_FORMAT))
		logger.addHandler(handler)

	return LoggerWrapper(logger, request_id)
