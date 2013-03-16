import database, pymongo, util, re
from bson.code import Code

class MongoDb:
	def __init__(self, database, host = "127.0.0.1", port = 27017):
		self.__db = pymongo.MongoClient(host, port)[database]

	def find(self, collection, filter = None, fields = None, sorting = None, limit = None, skip = None):
		if fields is None:
			fields = { "_id": False }

		cur = self.__db[collection].find(filter, fields)

		if not sorting is None:
			if sorting[1]:
				order = pymongo.ASCENDING
			else:
				order = pymongo.DESCENDING

			cur = cur.sort(sorting[0], order)

		if not limit is None:
			cur = cur.limit(limit)

		if not skip is None:
			cur = cur.skip(skip)

		return cur

	def find_one(self, collection, filter, fields = None):
		if fields is None:
			fields = { "_id": False }

		return self.__db[collection].find_one(filter, fields)

	def save(self, collection, document):
		self.__db[collection].save(document)

	def update(self, collection, filter, document):
		self.__db[collection].update(filter, document)

	def remove(self, collection, filter = None):
		self.__db[collection].remove(filter)

	def count(self, collection, filter = None):
		# pymongo doesn't support a filter in the count() method :(
		return self.find(collection, filter).count()

	def map_reduce(self, source, map_function, reduce_function, destination):
		return self.__db[source].map_reduce(map_function, reduce_function, destination)

class MongoUserDb(MongoDb, database.UserDb):
	def __init__(self, database, host = "127.0.0.1", port = 27017):
		MongoDb.__init__(self, database, host, port)

	def get_user(self, username):
		return self.find_one("users", { "name": username }, { "_id": False, "name": True, "firstname": True, "lastname": True,
		                                                      "email": True, "password": True, "gender": True, "timestamp": True,
		                                                      "avatar": True, "blocked": True, "protected": True })

	def search_user(self, query):
		filter = { "$or": [] }

		# search username & email:
		q = ".*%s.*" % re.escape(query.strip())

		filter["$or"].append({ "name": { "$regex": q } })
		filter["$or"].append({ "email": { "$regex": q } })

		# search first and lastname
		regex = re.compile("\W")
		parts = []

		for p in re.compile("\s").split(query):
			parts.append(regex.sub("", p).strip())

		for i in range(1, len(parts) + 1):
			a = " ".join(parts[:i]).strip()
			b = " ".join(parts[i:]).strip()


			if len(b) > 0:
				a = ".*%s.*" % re.escape(a)
				b = ".*%s.*" % re.escape(b)

				filter["$or"].append({ "$and": [ { "firstname": {  "$regex": a } }, { "lastname": { "$regex": b } } ] })
				filter["$or"].append({ "$and": [ { "lastname": {  "$regex": a } }, { "firstname": { "$regex": b } } ] })
			else:
				a = ".*%s.*" % re.escape(a)

				filter["$or"].append({ "firstname": { "$regex": a } })
				filter["$or"].append({ "lastname": { "$regex": a } })

		return (user for user in self.find("users", filter, { "_id": False, "name": True, "firstname": True, "lastname": True,
		                                                      "protected": True, "avatar": True, "gender": True }))

	def create_user(self, username, email, firstname, lastname, password, gender):
		self.save("users", { "name": username,
		                     "email": email,
		                     "firstname": firstname,
		                     "lastname": lastname,
		                     "password": password,
		                     "gender": gender,
		                     "timestamp": util.now(),
		                     "avatar": None,
		                     "blocked": False,
		                     "protected": True })

	def update_user_details(self, username, email, firstname, lastname, gender):
		self.update("users", { "name": username },
		                     { "$set": {
		                          "email": email,
		                          "firstname": firstname,
		                          "lastname": lastname,
		                          "gender": gender,
		                     } })

	def update_user_password(self, username, password):
		self.update("users", { "name": username }, { "$set": { "password": password } })

	def get_user_password(self, username):
		pwd = self.find_one("users", { "name": username }, [ "password" ])

		if not pwd is None:
			return pwd["password"]

		return None

	def update_avatar(self, username, avatar):
		self.update("users", { "name": username }, { "$set": { "avatar": avatar } })

	def block_user(self, username, blocked):
		self.update("users", { "name": username }, { "$set": { "blocked": blocked } })

	def user_is_blocked(self, username):
		flag = self.find_one("users", { "name": username }, [ "blocked" ])

		if flag is None:
			return False

		return flag["blocked"]

	def user_exists(self, username):
		return bool(self.count("users", { "name": username }))

	def email_assigned(self, email):
		return bool(self.count("users", { "email": email }))

	def user_request_code_exists(self, code):
		return bool(self.count("user_requests", { "code": code }))

	def remove_user_request(self, code):
		self.remove("user_requests", { "code": code })

	def create_user_request(self, username, email, code):
		self.save("user_requests", { "name": username,
		                             "email": email,
		                             "code": code })

	def username_requested(self, username):
		return bool(self.count("user_requests", { "name": username }))

class MongoObjectDb(MongoDb, database.ObjectDb):
	def __init__(self, database, host = "127.0.0.1", port = 27017):
		MongoDb.__init__(self, database, host, port)

	def create_object(self, guid, source):
		self.save("objects", { "guid": guid,
		                       "source": source,
		                       "locked": False,
		                       "tags": [],
		                       "score": { "up": 0, "down": 0, "fav": 0, "total": 0 },
		                       "timestamp": util.now() })

	def lock_object(self, guid, locked):
		self.update("objects", { "guid": guid }, { "$set": { "locked": locked } })

	def is_locked(self, guid):
		flag = self.find_one("objects", { "guid": guid }, [ "locked" ])

		if flag is None:
			return False

		return flag["locked"]

	def remove_object(self, guid):
		self.remove("objects", { "guid": guid })

	def get_object(self, guid):
		return self.find_one("objects", { "guid": guid }, { "_id": False, "guid": True, "source": True,
		                                                    "locked": True, "tags": True, "score": True, "timestamp": True } )

	def get_objects(self, page = 0, page_size = 10, tag_filter = None):
		filter = []

		if not tag_filter is None:
			filter = { "tags": tag_filter }

		if len(filter) == 0:
			filter = None

		return self.find("objects", sorting = [ "timestamp", False ], limit = page_size, skip = page * page_size,
		                 fields = { "_id": False, "guid": True, "source": True, "locked": True, "tags": True,
				            "score": True, "timestamp": True }, filter = filter)

	def get_tagged_objects(self, tag, page = 0, page_size = 10):
		return self.get_objects(page, page_size, tag_filter = tag)

	def get_popular_objects(self, page = 0, page_size = 10): return None

	def get_random_objects(self, page = 0, page_size = 10): return None

	def add_tags(self, guid, tags):
		self.update("objects", { "guid": guid }, { "$addToSet": { "tags": { "$each": tags } } })

	def build_tag_statistic(self):
		map_function = Code("function() {"
		                    "	if(!this.tags) return;"
	                            "	for(var i in this.tags) {"
		                    "		emit(this.tags[i], 1);"
		                    "	}"
		                    "}")

		reduce_function = Code("function(key, values) { return values.length; }")

		self.map_reduce("objects", map_function, reduce_function, "tag_statistic")

	def get_tags(self, limit = None):
		tags = []

		for tag in self.find("tag_statistic", sorting = [ "value", False ], fields = [ "_id", "value" ], limit = limit):
			tags.append( { "tag": tag["_id"], "count": tag["value"] } )

		return tags

	def rate(self, guid, username, up = True): return

	def user_can_rate(self, guid, username): return False

	def add_comment(self, guid, username, text): return

	def get_comments(self, guid, page = 0, page_size = 10): return None

	def favor_object(self, guid, username, favor = True): return

	def is_favorite(self, guid, username): return False

	def get_favorites(self, username, page = 0, page_size = 10): return None

	def recommend(self, guid, username, receivers): return

	def get_recommendations(self, username, page = 0, page_size = 10): return None
