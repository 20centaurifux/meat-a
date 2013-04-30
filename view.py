# -*- coding: utf-8 -*-

from util import to_json

class View(object):
	def __init__(self, content_type, status):
		self.content_type = content_type
		self.status = status
		self.model = None

	def bind(self, model):
		self.model = model

	def render(self):
		return self.model

class JSONView(View):
	def __init__(self, status):
		View.__init__(self, "application/json", status)

	def render(self):
		return to_json(self.model)
