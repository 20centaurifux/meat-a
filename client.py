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
#  @file client.py
#  An example client.

## @package client
#  An example client.

import urllib, urllib2, json, util, os, itertools, mimetools, mimetypes

## Class used to create multi-part forms.
class MultiPartForm:
	def __init__(self):
		## Fields stored in the form.	
		self.form_fields = []
		## Files stored in the form.
		self.files = []
		## The boundary.	
		self.boundary = mimetools.choose_boundary()

	## Gets content type of the form.
	#  @return a string
	def get_content_type(self):
		return "multipart/form-data; boundary=%s" % self.boundary

	## Adds a new field to the form.
	#  @param name name of the field
	#  @param value value of the field
	def add_field(self, name, value):
		self.form_fields.append((name, value))

	## Adds a file to the form.
	#  @param fieldname name of the field
	#  @param filename name of the file to add
	#  @param file_handle handler used to read file content
	#  @param mimetype content type of the file
	def add_file(self, fieldname, filename, file_handle, mimetype=None):
		body = file_handle.read()

		if mimetype is None:
			mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"

		self.files.append((fieldname, filename, mimetype, body))

	## Converts the multi-part form to a string.
	#  @return a string
	def __str__(self):
		parts = []
		part_boundary = "--" + self.boundary
	   
		parts.extend([ part_boundary, 'Content-Disposition: form-data; name="%s"' % name, "", value, ] for name, value in self.form_fields)
		parts.extend([ part_boundary, 'Content-Disposition: file; name="%s"; filename="%s"' % (field_name, filename),
		               "Content-Type: %s" % content_type, "", body, ] for field_name, filename, content_type, body in self.files)
	   
		flattened = list(itertools.chain(*parts))
		flattened.append("--" + self.boundary + "--")
		flattened.append("")

		return "\r\n".join(flattened)

## Example client.
class Client:
	## The constructor.
	#  @param url url of the webservice
	#  @param port port of the webservice
	def __init__(self, url, port):
		## URL of the webservice.
		self.url = url
		## Port of the webservice.
		self.port = port

	## Requests a user account.
	#  @param username requested username
	#  @param email email address of the account
	#  @return server response (as string)
	def request_account(self, username, email):
		params = { "username": username, "email": email }
		data = urllib.urlencode(params)

		req = urllib2.Request(self.__build_url__("/account/new"), data)

		return urllib2.urlopen(req).read()

	## Disables a user account.
	#  @param username user to disable
	#  @param password user password (plaintext)
	#  @param email email address of the user
	#  @return server response (as string)
	def disable_user(self, username, password, email):
		return self.__post__("/account/disable", password, username = username, email = email)

	## Requests a new password.
	#  @param username a username
	#  @param email email address of the user
	#  @return server response (as string)
	def request_password(self, username, email):
		params = { "username": username, "email": email }
		url = "%s%s" % (self.__build_url__("/account/password/request?"), urllib.urlencode(params))

		return self.get(url)

	## Tests user authentication.
	#  @param username a username
	#  @param password password of the user (plaintext)
	#  @return server response (as string)
	def test_authentication(self, username, password):
		return self.__post__("/account/authentication/test", password, username = username)

	## Updates a user password.
	#  @param username a username
	#  @param old_password password of the account (plaintext)
	#  @param new_password new password to set (plaintext)
	#  @return server response (as string)
	def update_password(self, username, old_password, new_password):
		return self.__post__("/account/password/update", old_password, username = username, old_password = old_password, new_password = new_password)

	## Updates user details.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param email email address to set
	#  @param firstname firstname to set
	#  @param lastname lastname to set
	#  @param gender gender to set
	#  @param language language to set
	#  @param protected protected status to set
	#  @return server response (as string)
	def update_user_details(self, username, password, email, firstname, lastname, gender, language, protected):
		return self.__post__("/account/update", password, username = username, email = email, firstname = firstname, lastname = lastname,
		                     gender = gender, language = language, protected = protected)

	## Gets details of a user account.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param name name of an existing user account
	#  @return server response (as string)
	def get_user_details(self, username, password, name):
		return self.__post__("/account/details", password, username = username, name = name)

	## Updates an avatar.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param filename name of a file to upload
	#  @return server response (as string)
	def update_avatar(self, username, password, filename):
		form = MultiPartForm()
		t = util.unix_timestamp()
		sign = util.sign_message(util.hash(password), filename = os.path.basename(filename), username = username, timestamp = t)

		form.add_field("filename", os.path.basename(filename))
		form.add_field("username", username)
		form.add_field("signature", sign)
		form.add_field("timestamp", str(t))

		with open(filename, "rb") as f:
			form.add_file("file", filename, f)

		body = str(form)

		req = urllib2.Request(self.__build_url__("/account/avatar/update"))
		req.add_header("Content-type", form.get_content_type())
		req.add_header("Content-length", len(body))
		req.add_data(body)

		return urllib2.urlopen(req).read()

	## Gets favorites of a user.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param page page number
	#  @param page_size size of each page
	#  @return server response (as string)
	def get_favorites(self, username, password, page, page_size):
		return self.__post__("/account/favorites", password, username = username, page = page, page_size = page_size)

	## Searches the user data store.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param query a search query
	#  @return server response (as string)
	def find_user(self, username, password, query):
		return self.__post__("/account/search", password, username = username, query = query)

	## Gets object details.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object.
	#  @return server response (as string)
	def get_object(self, username, password, guid):
		return self.__post__("/object/details", password, username = username, guid = guid)

	## Gets objects.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param page page number
	#  @param page_size size of each page
	#  @return server response (as string)
	def get_objects(self, username, password, page, page_size):
		return self.__post__("/objects", password, username = username, page = page, page_size = page_size)

	## Gets objects assigned to an tag.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param tag a tag
	#  @param page page number
	#  @param page_size size of each page
	#  @return server response (as string)
	def get_tagged_objects(self, username, password, tag, page, page_size):
		return self.__post__("/objects/tag", password, username = username, tag = tag, page = page, page_size = page_size)

	## Gets random objects.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param page_size the page size
	#  @return server response (as string)
	def get_random_objects(self, username, password, page_size):
		return self.__post__("/objects/random", password, username = username, page_size = page_size)

	## Gets most popular objects.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param page page number
	#  @param page_size size of each page
	#  @return server response (as string)
	def get_popular_objects(self, username, password, page, page_size):
		return self.__post__("/objects/popular", password, username = username, page = page, page_size = page_size)

	## Adds tags to an object.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object
	#  @param tags array containing tags
	#  @return server response (as string)
	def add_tags(self, username, password, guid, tags):
		t = util.unix_timestamp()
		sign = util.sign_message(util.hash(password), username = username, timestamp = t, guid = guid, tags = tags)
		data = urllib.urlencode({ "username": username, "timestamp": t, "guid": guid, "tags": json.dumps(tags)[1:-1], "signature": sign })

		req = urllib2.Request(self.__build_url__("/object/tags/add"), data)
		res = urllib2.urlopen(req)

		return res.read()

	## Upvotes/Downvotes an object.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object
	#  @param up True to upvote
	#  @return server response (as string)
	def rate(self, username, password, guid, up = True):
		return self.__post__("/object/rate", password, username = username, guid = guid, up = str(up).lower())

	## Adds an object to the favorites list of a user.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object
	#  @param favor True to add the object to the favorites list
	#  @return server response (as string)
	def favor(self, username, password, guid, favor = True):
		return self.__post__("/object/favor", password, username = username, guid = guid, favor = str(favor).lower())

	## Adds a comment to an object.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object
	#  @param text text to append
	#  @return server response (as string)
	def add_comment(self, username, password, guid, text):
		return self.__post__("/object/comments/add", password, username = username, guid = guid, text = text)

	## Gets comments assigned to an object.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object
	#  @param page page number
	#  @param page_size size of each page
	#  @return server response (as string)
	def get_comments(self, username, password, guid, page, page_size):
		return self.__post__("/object/comments", password, username = username, guid = guid, page = page, page_size = page_size)

	## Lets a user follow another user.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param user name of a user account
	#  @param follow True to follow a user
	#  @return server response (as string)
	def follow(self, username, password, user, follow = True):
		return self.__post__("/account/follow", password, username = username, user = user, follow = str(follow).lower())

	## Recommends an object to friends.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object
	#  @param receivers array holding receivers
	#  @return server response (as string)
	def recommend(self, username, password, guid, receivers):
		t = util.unix_timestamp()
		sign = util.sign_message(util.hash(password), username = username, timestamp = t, guid = guid, receivers = receivers)
		data = urllib.urlencode({ "username": username, "timestamp": t, "guid": guid, "receivers": json.dumps(receivers)[1:-1], "signature": sign })

		req = urllib2.Request(self.__build_url__("/object/recommend"), data)
		res = urllib2.urlopen(req)

		return res.read()

	## Gets objects recommended to a user.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param page page number
	#  @param page_size size of each page
	#  @return server response (as string)
	def get_recommendations(self, username, password, page, page_size):
		return self.__post__("/account/recommendations", password, username = username, page = page, page_size = page_size)

	## Reports abuse.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param guid guid of an object to report
	#  @return server response (as string)
	def report_abuse(self, username, password, guid):
		return self.__post__("/object/abuse", password, username = username, guid = guid)

	## Gets messages sent to a user.
	#  @param username a username
	#  @param password user password (plaintext)
	#  @param limit maximum number of messages to receive
	#  @param older_than filter to get only messages older than the specified timestamp
	#  @return server response (as string)
	def get_messages(self, username, password, limit, older_than):
		if older_than is None:
			older_than = "null"

		return self.__post__("/account/messages", password, username = username, limit = limit, older_than = older_than)

	## Sends a GET request to a server.
	#  @param url an URL
	#  @return server response (as string)
	def get(self, url):
		req = urllib2.Request(url)

		return urllib2.urlopen(req).read()

	def __build_url__(self, path):
		return "%s:%d%s" % (self.url, self.port, path)

	def __post__(self, path, secret, **kwargs):
		t = util.unix_timestamp()

		kwargs["timestamp"] = t
		sign = util.sign_message(util.hash(secret), **kwargs)
		kwargs["signature"] = sign

		data = urllib.urlencode(kwargs)

		req = urllib2.Request(self.__build_url__(path), data)
		res = urllib2.urlopen(req)

		return res.read()
