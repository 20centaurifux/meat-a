import urllib, urllib2, json, util, os, itertools, mimetools, mimetypes

class MultiPartForm:
	def __init__(self):
		self.form_fields = []
		self.files = []
		self.boundary = mimetools.choose_boundary()

	def get_content_type(self):
		return "multipart/form-data; boundary=%s" % self.boundary

	def add_field(self, name, value):
		self.form_fields.append((name, value))

	def add_file(self, fieldname, filename, fileHandle, mimetype=None):
		body = fileHandle.read()

		if mimetype is None:
			mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"

		self.files.append((fieldname, filename, mimetype, body))

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

class Client:
	def __init__(self, url, port):
		self.url = url
		self.port = port

	def request_account(self, username, email):
		params = { "username": username, "email": email }
		data = urllib.urlencode(params)

		req = urllib2.Request(self.__build_url__("/account/new"), data)

		return urllib2.urlopen(req).read()

	def disable_user(self, username, password, email):
		return self.__post__("/account/disable", password, username = username, email = email)

	def request_password(self, username, email):
		params = { "username": username, "email": email }
		url = "%s%s" % (self.__build_url__("/account/password/request?"), urllib.urlencode(params))

		return self.get(url)

	def update_password(self, username, old_password, new_password):
		return self.__post__("/account/password/update", old_password, username = username, old_password = old_password, new_password = new_password)

	def update_user_details(self, username, password, email, firstname, lastname, gender, language, protected):
		return self.__post__("/account/update", password, username = username, email = email, firstname = firstname, lastname = lastname,
		                     gender = gender, language = language, protected = protected)

	def get_user_details(self, username, password, name):
		return self.__post__("/account/details", password, username = username, name = name)

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

	def get_favorites(self, username, password, page, page_size):
		return self.__post__("/account/favorites", password, username = username, page = page, page_size = page_size)

	def find_user(self, username, password, query):
		return self.__post__("/account/search", password, username = username, query = query)

	def get_object(self, username, password, guid):
		return self.__post__("/object/details", password, username = username, guid = guid)

	def get_objects(self, username, password, page, page_size):
		return self.__post__("/objects", password, username = username, page = page, page_size = page_size)

	def get_tagged_objects(self, username, password, tag, page, page_size):
		return self.__post__("/objects/tag", password, username = username, tag = tag, page = page, page_size = page_size)

	def get_random_objects(self, username, password, page_size):
		return self.__post__("/objects/random", password, username = username, page_size = page_size)

	def get_popular_objects(self, username, password, page, page_size):
		return self.__post__("/objects/popular", password, username = username, page = page, page_size = page_size)

	def add_tags(self, username, password, guid, tags):
		t = util.unix_timestamp()
		sign = util.sign_message(util.hash(password), username = username, timestamp = t, guid = guid, tags = tags)
		data = urllib.urlencode({ "username": username, "timestamp": t, "guid": guid, "tags": json.dumps(tags)[1:-1], "signature": sign })

		req = urllib2.Request(self.__build_url__("/object/tags/add"), data)
		res = urllib2.urlopen(req)

		return res.read()

	def rate(self, username, password, guid, up = True):
		return self.__post__("/object/rate", password, username = username, guid = guid, up = str(up).lower())

	def favor(self, username, password, guid, favor = True):
		return self.__post__("/object/favor", password, username = username, guid = guid, favor = str(favor).lower())

	def add_comment(self, username, password, guid, text):
		return self.__post__("/object/comments/add", password, username = username, guid = guid, text = text)

	def get_comments(self, username, password, guid, page, page_size):
		return self.__post__("/object/comments", password, username = username, guid = guid, page = page, page_size = page_size)

	def follow(self, username, password, user, follow = True):
		return self.__post__("/account/follow", password, username = username, user = user, follow = str(follow).lower())

	def recommend(self, username, password, guid, receivers):
		t = util.unix_timestamp()
		sign = util.sign_message(util.hash(password), username = username, timestamp = t, guid = guid, receivers = receivers)
		data = urllib.urlencode({ "username": username, "timestamp": t, "guid": guid, "receivers": json.dumps(receivers)[1:-1], "signature": sign })

		req = urllib2.Request(self.__build_url__("/object/recommend"), data)
		res = urllib2.urlopen(req)

		return res.read()

	def get_recommendations(self, username, password, page, page_size):
		return self.__post__("/account/recommendations", password, username = username, page = page, page_size = page_size)

	def get_messages(self, username, password, limit, older_than):
		if older_than is None:
			older_than = "null"

		return self.__post__("/account/messages", password, username = username, limit = limit, older_than = older_than)

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
