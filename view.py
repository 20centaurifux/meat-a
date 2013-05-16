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
##
#  @file view.py
#  Base class for views and implementations.

## @package view
#  Base class for views and implementations.

from util import to_json

## A base class views. A view can be exported to a string which contains binded data.
class View(object):
	## The constructor.
	#  @param content_type content type of the view (e.g. "text/html")
	#  @param status an HTTP status code
	def __init__(self, content_type, status):
		## Content type of the view.
		self.content_type = content_type
		## An HTTP status.
		self.status = status
		## Data stored in the view.
		self.model = None

	## Binds data.
	#  @param model data to bind
	def bind(self, model):
		self.model = model

	## Converts the view to a string.
	#  @return a string
	def render(self):
		return self.model

## A view generating a JSON string.
class JSONView(View):
	## The constructor.
	#  @param status an HTTP status code
	def __init__(self, status):
		View.__init__(self, "application/json", status)

	## Converts the assigned model to a JSON string.
	#  @return a JSON string
	def render(self):
		return to_json(self.model)
