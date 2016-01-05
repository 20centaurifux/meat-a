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
#  @file mongodb.py
#  MongoDB database classes.

## @package mongodb
#  MongoDB database classes.

import database, pymongo, util, re
from bson.code import Code
from bson import ObjectId
from random import random
from exception import ConstraintViolationException, InternalFailureException

## Base class for MongoDB database classes. This class provides access to the
#  database and some wrapped pymongo functions.
class MongoDb(database.DbUtil):
	## The constructor.
	#  There are two ways to connect to a Mongo database. When specifying
	#  "host" and "port" this class will create its own MongoClient instance to
	#  connect to the database. It's also possible to use an already existing
	#  MongoClient instance using the "client" parameter. Kindly note that this
	#  class will not close the connection if you have specified the "client"
	#  parameter. The benefit of this option is that you can share one MongoClient
	#  instance between multiple objects inherited from this class.
	#  @param database database name
	#  @param kwargs "host" & "port" or "client" to share an existing MongoClient instance
	def __init__(self, database, **kwargs):
		self.__database = database
		self.__db = None
		self.__open = False
		self.__client = None
		self.__shared_client = False

		if kwargs.has_key("host") and kwargs.has_key("port"):
			self.__host = kwargs["host"]
			self.__port = kwargs["port"]
		else:
			self.__client = kwargs["client"]
			self.__shared_client = True

	## Closes the database connection.
	def close(self):
		if self.__open and not self.__shared_client:
			self.__client.disconnect()
			self.__client = None
			self.__open = False

	## Deletes data from all tables.
	def clear_tables(self):
		self.__connect__()

		for table in [ "users", "user_requests", "password_requests", "objects", "streams", "mails", "requests" ]:
			self.remove(table)

	## Wrapper of the pymongo::find() function.
	#  @param collection name of a collection
	#  @param filter dictionary holding filter settings
	#  @param fields fields to return (e.g. { "_id": False, "name": True })
	#  @param sorting the sort order (e.g. [ "timestamp", -1 ])
	#  @param limit maximum number of records to return
	#  @param skip number of records to skip
	#  @return dictionary containing documents
	def find(self, collection, filter = None, fields = None, sorting = None, limit = None, skip = None):
		self.__connect__()

		if fields is None:
			fields = { "_id": False }

		cur = self.__db[collection].find(filter, fields)

		if not sorting is None:
			cur = cur.sort(sorting[0], sorting[1])

		if not limit is None:
			cur = cur.limit(limit)

		if not skip is None:
			cur = cur.skip(skip)

		return cur

	## Wrapper of the pymongo::find_and_modify() function.
	#  @param collection name of a collection
	#  @param query a search query
	#  @param update an update query
	#  @param upsert True to create a new document
	#  @param sort determines which document the operation will modify if the query selects multiple documents
	#  @return the found document or None
	def find_and_modify(self, collection, query = None, update = None, upsert = False, sort = None):
		self.__connect__()

		result = self.__db[collection].find_and_modify(query, update, upsert, sort)

		if not result:
			return None

		return result

	## Wrapper of the pymongo::find_one() function.
	#  @param collection name of a collection
	#  @param filter dictionary holding filter settings
	#  @param fields fields to return (e.g. { "_id": False, "name": True })
	#  @return the found document
	def find_one(self, collection, filter, fields = None):
		self.__connect__()

		if fields is None:
			fields = { "_id": False }

		return self.__db[collection].find_one(filter, fields)

	## Wrapper of the pymongo::save function.
	#  @param collection name of a collection
	#  @param document document to save
	def save(self, collection, document):
		self.__connect__()
		self.__db[collection].save(document)

	## Wrapper of the pymongo::update function.
	#  @param collection name of a collection
	#  @param filter dictionary holding filter settings
	#  @param document document to update
	def update(self, collection, filter, document):
		self.__connect__()
		self.__db[collection].update(filter, document)

	## Wrapper of the pymongo::remove function.
	#  @param collection name of a collection
	#  @param filter dictionary holding filter settings
	def remove(self, collection, filter = None):
		self.__connect__()
		self.__db[collection].remove(filter)

	## Counts documents in a collection.
	#  @param collection name of a collection
	#  @param filter dictionary holding filter settings
	#  @return number of found documents
	def count(self, collection, filter = None):
		self.__connect__()

		# pymongo doesn't support a filter in the count() method :(
		return self.find(collection, filter).count()

	## Wrapper of the pymongo::map_reduce() function.
	#  @param source the source collection
	#  @param map_function the map function
	#  @param reduce_function the reduce function
	#  @param destination collection to store the result
	#  @return documents stored in the destination collection
	def map_reduce(self, source, map_function, reduce_function, destination):
		self.__connect__()

		return self.__db[source].map_reduce(map_function, reduce_function, destination)

	def __connect__(self):
		if not self.__open:
			if self.__client is None:
				self.__client = pymongo.MongoClient(self.__host, self.__port)

			self.__db = self.__client[self.__database]
			self.__open = True

			# create indices:
			self.__db.users.ensure_index("name", 1)
			self.__db.users.ensure_index("email", 1)
			self.__db.users.ensure_index("blocked", 1)
			self.__db.users.ensure_index("following", 1)
			self.__db.objects.ensure_index("random", 1)
			self.__db.objects.ensure_index("score_total", -1)
			self.__db.objects.ensure_index("timestamp", -1)
			self.__db.objects.ensure_index("fans", 1)
			self.__db.objects.ensure_index("tags", 1)
			self.__db.objects.ensure_index("voters", 1)
			self.__db.objects.ensure_index([ ("receiver", 1), ("timestamp", -1) ])
			self.__db.mails.ensure_index("lifetime", 1)
			self.__db.requests.ensure_index([ ("ip", 1), ("lifetime", -1), ("type_id", 1) ])
			self.__db.requests.ensure_index("lifetime", 1)

## Implementation of database.UserDb base class using MongoDB as backend.
class MongoUserDb(MongoDb, database.UserDb):
	def __init__(self, database, **kwargs):
		MongoDb.__init__(self, database, **kwargs)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def get_user(self, username):
		return self.__get_user__({ "name": username })

	def get_user_by_email(self, email):
		return self.__get_user__({ "email": email })

	def search_user(self, query):
		filter = { "$or": [] }

		# search username & email:
		q = ".*%s.*" % re.escape(query.strip())

		filter["$or"].append({ "name": { "$regex": q } })
		filter["$or"].append({ "email": { "$regex": q } })

		# search first and lastname
		regex = re.compile("\W")
		parts = []

		map(lambda p: parts.append(regex.sub("", p).strip()), re.compile("\s").split(query))

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

		filter = { "$and": [ { "blocked": False }, filter ] }

		return [ user for user in self.find("users", filter, { "_id": False, "name": True, "firstname": True, "lastname": True,
		                                                       "protected": True, "avatar": True, "gender": True, "email": True,
		                                                       "timestamp": True, "following": True }) ]

	def create_user(self, username, email, password, firstname = None, lastname = None, gender = None, language = None, protected = True):
		user = self.find_and_modify("users", { "$or": [ { "name": username }, { "$and": [ { "email": email }, { "blocked": False } ] } ] },
		                            { "name": username,
		                              "email": email,
		                              "firstname": firstname,
		                              "lastname": lastname,
		                              "password": password,
		                              "gender": gender,
		                              "following": [],
		                              "timestamp": util.now(),
		                              "avatar": None,
		                              "language": language,
		                              "blocked": False,
		                              "protected": protected },
		                              True)

		if not user is None:
			raise ConstraintViolationException("Username or email address already assigned.")

	def update_user_details(self, username, email, firstname, lastname, gender, language, protected):
		self.update("users", { "name": username },
		                     { "$set": {
		                          "email": email,
		                          "firstname": firstname,
		                          "lastname": lastname,
		                          "gender": gender,
		                          "language": language,
		                          "protected": protected
		                     } })

	def update_user_password(self, username, password):
		self.find_and_modify("users", { "name": username }, { "$set": { "password": password } })

	def get_user_password(self, username):
		pwd = self.find_one("users", { "name": username }, [ "password" ])

		if not pwd is None:
			return pwd["password"]

		return None

	def update_avatar(self, username, avatar):
		self.update("users", { "name": username }, { "$set": { "avatar": avatar } })

	def block_user(self, username, blocked = True):
		self.update("users", { "name": username }, { "$set": { "blocked": blocked } })

	def user_is_blocked(self, username):
		flag = self.find_one("users", { "name": username }, [ "blocked" ])

		if flag is None:
			return False

		return flag["blocked"]

	def user_exists(self, username):
		return bool(self.count("users", { "name": username }))

	def email_assigned(self, email):
		return bool(self.count("users", { "$and": [ { "email": email }, { "blocked": False } ] }))

	def user_request_id_exists(self, id):
		return bool(self.count("user_requests", { "$and": [ { "id": id }, { "lifetime": { "$gte": util.now() } } ] }))

	def get_user_request(self, id):
		return self.find_one("user_requests", { "$and": [ { "id": id }, { "lifetime": { "$gte": util.now() } } ] },
		                     { "_id": False, "name": True, "email": True, "code": True })

	def remove_user_request(self, id):
		self.remove("user_requests", { "id": id })

	def create_user_request(self, username, email, id, code, lifetime = 20):
		request = self.find_and_modify("user_requests",
	                                       { "$and": [ { "$or": [ { "name": username }, { "code": code } ] }, { "lifetime": { "$gte": util.now() } } ] },
                                               { "name": username, "email": email, "id": id, "code": code, "lifetime": lifetime * 1000 + util.now() },
                                               True)

		if not request is None:
			raise ConstraintViolationException("Username already requested.")

	def username_requested(self, username):
		return bool(self.count("user_requests", { "$and": [ { "name": username }, { "lifetime": { "$gte": util.now() } } ] }))

	def password_request_id_exists(self, id):
		return bool(self.count("password_requests", { "$and": [ { "id": id }, { "lifetime": { "$gte": util.now() } } ] }))

	def get_password_request(self, id):
		result = self.find_one("password_requests", { "$and": [ { "id": id }, { "lifetime": { "$gte": util.now() } } ] },
		                       { "_id": False, "name": True, "code": True })

		return result

	def remove_password_request(self, id):
		self.remove("password_requests", { "id": id })

	def create_password_request(self, username, id, code, lifetime = 60):
		request = self.find_and_modify("password_requests",
	                                       { "code": code },
                                               { "name": username, "id", id, "code": code, "lifetime": lifetime * 1000 + util.now() },
                                               True)

		if not request is None:
			raise ConstraintViolationException("Password request code does already exist.")

	def follow(self, user1, user2, follow = True):
		if follow:
			query = { "name": user1, "following": { "$ne": user2 } };
			update = { "$push": { "following": user2 } }
		else:
			query = { "name": user1, "following": user2 };
			update = { "$pull": { "following": user2 } }

		self.update("users", query, update)

	def is_following(self, user1, user2):
		return bool(self.count("users", { "$and": [ { "name": user1 }, { "following": user2 } ] }))

	def __get_user__(self, filter):
		return self.find_one("users", filter, { "_id": False, "name": True, "firstname": True, "lastname": True,
		                                        "email": True, "password": True, "gender": True, "timestamp": True,
		                                        "avatar": True, "blocked": True, "protected": True, "following": True,
		                                        "language": True })

## Implementation of database.ObjectDb base class using MongoDB as backend.
class MongoObjectDb(MongoDb, database.ObjectDb):
	def __init__(self, database, **kwargs):
		MongoDb.__init__(self, database, **kwargs)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def create_object(self, guid, source):
		self.save("objects", { "guid": guid,
		                       "source": source,
		                       "locked": False,
		                       "tags": [],
		                       "score": { "up": 0, "down": 0, "fav": 0 },
		                       "score_total": 0,
		                       "voters": [],
		                       "fans": [],
		                       "recommendations": [],
		                       "timestamp": util.now(),
		                       "comments_n": 0,
		                       "comments": [],
		                       "reported": False,
		                       "random": random() })

	def lock_object(self, guid, locked = True):
		self.update("objects", { "guid": guid }, { "$set": { "locked": locked } })

	def is_locked(self, guid):
		flag = self.find_one("objects", { "guid": guid }, [ "locked" ])

		if flag is None:
			return False

		return flag["locked"]

	def remove_object(self, guid):
		self.remove("objects", { "guid": guid })

	def object_exists(self, guid):
		return bool(self.count("objects", { "guid": guid }))

	def get_object(self, guid):
		obj = self.find_one("objects", { "guid": guid }, { "_id": False, "guid": True, "source": True, "locked": True,
		                                                   "tags": True, "score": True, "score_total": True, "timestamp": True,
		                                                   "comments_n": True, "reported": True } )

		return self.__prepare_object__(obj)

	def get_objects(self, page = 0, page_size = 10, filter = None, sorting = [ "timestamp", -1 ]):
		if page_size > 1:
			objs = self.find("objects", sorting = sorting, limit = page_size, skip = page * page_size,
			                 fields = { "_id": False, "guid": True, "source": True, "locked": True, "tags": True,
			                            "score": True, "score_total": True, "timestamp": True, "comments_n": True }, filter = filter)

			result = []

			map(lambda obj: result.append(self.__prepare_object__(obj)), objs)

			return result
		else:
			obj = self.find_one("objects", fields = { "_id": False, "guid": True, "source": True, "locked": True, "tags": True,
			                                           "score": True, "score_total": True, "timestamp": True, "comments_n": True }, filter = filter)

			return self.__prepare_object__(obj)

	def get_tagged_objects(self, tag, page = 0, page_size = 10):
		return self.get_objects(page, page_size, { "tags": tag })

	def get_popular_objects(self, page = 0, page_size = 10):
		return self.get_objects(page, page_size, sorting = [ "score_total", -1 ])

	def get_random_objects(self, page_size = 10):
		result = []
		result_append = result.append
		limit = page_size * 3
		count = 0

		while len(result) != page_size and count < limit:
			rnd = random()

			obj = self.get_objects(0, 1, { "random": { "$gte": rnd } })

			if obj is None:
				obj = self.get_objects(0, 1, { "random": { "$lte": rnd } })

			if not obj is None:
				exists = False

				for o in result:
					if o["guid"] == obj["guid"]:
						exists = True
						break

				if not exists:
					result_append(obj)

			count += 1

		return result

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

		map(lambda tag: tags.append( { "tag": tag["_id"], "count": tag["value"] } ), self.find("tag_statistic", sorting = [ "value", -1 ], fields = [ "_id", "value" ], limit = limit))

		return tags

	def rate(self, guid, username, up = True):
		query = { "guid": guid, "voters": { "$ne": username } };

		if up:
			update = { "$push": { "voters": username }, "$inc": { "score.up": 1, "score_total": 1 } }
		else:
			update = { "$push": { "voters": username }, "$inc": { "score.down": 1, "score_total": -1 } }

		self.update("objects", query, update)

	def user_can_rate(self, guid, username):
		if self.count("objects", { "$and": [ { "guid": guid }, { "voters": username } ] }) == 0:
			return True

		return False

	def add_comment(self, guid, username, text):
		comment = { "timestamp": util.now(), "user": username, "text": text }
		self.update("objects", { "guid": guid }, { "$push": { "comments": comment }, "$inc": { "comments_n": 1 } })

	def get_comments(self, guid, page = 0, page_size = 10):
		# get object:
		obj = self.find_one("objects", { "guid": guid }, { "_id": False, "comments": { "$slice": [ page * page_size, page_size ] } })

		if not obj is None:
			# fetch & insert additional user details:
			users = {}
			comments = obj["comments"]

			for comment in comments:
				name = comment["user"]

				try:
					user = users[name]

				except:
					user = self.find_one("users", { "name": name },
					                     { "_id": False, "name": True, "firstname": True, "lastname": True, "gender": True,
					                       "avatar": True, "blocked": True })
					users[name] = user

				if not user is None:
					comment["user"] = user

			return comments

		return []

	def favor_object(self, guid, username, favor = True):
		query = { "guid": guid, "": { "$ne": username } };

		if favor:
			update = { "$push": { "fans": { "user": username, "timestamp": util.now() } }, "$inc": { "score.up": 1, "score_total": 1 } }
		else:
			update = { "$pull": { "fans": { "user": username } }, "$inc": { "score.down": 1, "score_total": -1 } }

		self.update("objects", query, update)

	def is_favorite(self, guid, username):
		if self.count("objects", { "$and": [ { "guid": guid }, { "fans.user": username } ] }) > 0:
			return True

		return False

	def get_favorites(self, username, page = 0, page_size = 10):
		comments = [ c for c in self.get_objects(page, page_size, { "fans.user": username }) ]
		comments.sort(key = lambda x: x["timestamp"])

		return comments

	def recommend(self, guid, username, receivers):
		r = { "user": None, "timestamp": util.now() }

		query = { "guid": guid, "recommendations.user": { "$ne": "" } };
		update = { "$push": { "recommendations": None } }

		for receiver in receivers:
			r["user"] = receiver
			query["recommendations.user"]["$ne"] = receiver
			update["$push"]["recommendations"] = r

			self.update("objects", query, update)

	def get_recommendations(self, username, page = 0, page_size = 10):
		recommendations = [ r for r in self.get_objects(page, page_size, { "recommendations.user": username }) ]
		recommendations.sort(key = lambda x: x["timestamp"])

		return recommendations

	def recommendation_exists(self, guid, username):
		return bool(self.count("objects", { "guid": guid, "recommendations.user": username }))

	def report(self, guid):
		self.update("objects", { "guid": guid }, { "$set": { "reported": True } })

	def __prepare_object__(self, obj):
		if obj is None:
			return None

		obj["score"]["total"] = obj["score_total"]
		del obj["score_total"]

		return obj

## Implementation of database.StreamDb base class using MongoDB as backend.
class MongoStreamDb(MongoDb, database.StreamDb):
	def __init__(self, database, **kwargs):
		MongoDb.__init__(self, database, **kwargs)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def add_message(self, code, sender, receiver, **args):
		if code == MongoStreamDb.MessageType.RECOMMENDATION:
			self.__save_recommendation__(sender, receiver, **args)
		elif code == MongoStreamDb.MessageType.COMMENT:
			self.__save_comment__(sender, receiver, **args)
		elif code == MongoStreamDb.MessageType.FAVOR:
			self.__save_favor__(sender, receiver, **args)
		elif code == MongoStreamDb.MessageType.VOTE:
			self.__save_vote__(sender, receiver, **args)
		elif code == MongoStreamDb.MessageType.FOLLOW:
			self.__save_follow__(sender, receiver, **args)
		elif code == MongoStreamDb.MessageType.UNFOLLOW:
			self.__save_unfollow__(sender, receiver, **args)
		else:
			raise InternalFailureException("Invalid message code received.")

	def get_messages(self, user, limit = 100, older_than = None):
		# get messages:
		if older_than is None:
			result = self.find("streams", { "receiver": user }, { "_id": False }, ("timestamp", -1), limit)
		else:
			result = self.find("streams", { "$and": [ { "receiver": user }, { "timestamp": { "$lte": older_than } } ] }, { "_id": False }, ("timestamp", -1), limit)

		# fetch & insert additional user details:
		users = {}
		messages = []
		messages_append = messages.append

		for msg in result:
			name = msg["sender"]

			try:
				user = users[name]

			except:
				user = self.find_one("users", { "name": name },
				                     { "_id": False, "name": True, "firstname": True, "lastname": True, "avatar": True, "gender": True, "blocked": True })
				users[name] = user

			if not user is None:
				msg["sender"] = user

			messages_append(msg)

		return messages

	def __save_recommendation__(self, sender, receiver, **args):
		self.__test_args__([ "guid" ], [ "comment" ], **args)

		try:
			comment = args["comment"]

		except:
			comment = None

		self.save("streams", { "type_id": MongoStreamDb.MessageType.RECOMMENDATION,
		                       "timestamp": util.now(),
		                       "sender": sender,
		                       "receiver": receiver,
		                       "guid": args["guid"],
		                       "comment": None })

	def __save_comment__(self, sender, receiver, **args):
		self.__test_args__([ "guid", "comment" ], None, **args)

		self.save("streams", { "type_id": MongoStreamDb.MessageType.COMMENT,
		                       "timestamp": util.now(),
		                       "sender": sender,
		                       "receiver": receiver,
		                       "guid": args["guid"],
		                       "comment": args["comment"] })

	def __save_favor__(self, sender, receiver, **args):
		self.__test_args__([ "guid" ], None, **args)

		self.save("streams", { "type_id": MongoStreamDb.MessageType.FAVOR,
		                       "timestamp": util.now(),
		                       "sender": sender,
		                       "receiver": receiver,
		                       "guid": args["guid"] })

	def __save_vote__(self, sender, receiver, **args):
		self.__test_args__([ "guid", "up" ], None, **args)

		self.save("streams", { "type_id": MongoStreamDb.MessageType.VOTE,
		                       "timestamp": util.now(),
		                       "sender": sender,
		                       "receiver": receiver,
		                       "guid": args["guid"],
		                       "up": args["up"] })

	def __save_follow__(self, sender, receiver, **args):
		self.save("streams", { "type_id": MongoStreamDb.MessageType.FOLLOW,
		                       "timestamp": util.now(),
		                       "sender": sender,
		                       "receiver": receiver })

	def __save_unfollow__(self, sender, receiver, **args):
		self.save("streams", { "type_id": MongoStreamDb.MessageType.UNFOLLOW,
		                       "timestamp": util.now(),
		                       "sender": sender,
		                       "receiver": receiver })

	def __test_args__(self, required, optional, **args):
		keys = args.keys()

		if optional is None:
			optional = []

		for key in required:
			if not key in keys:
				raise InternalFailureException("Missing argument: '%s'" % key)

		for key in keys:
			if not key in required and not key in optional:
				raise InternalFailureException("Unknown argument: '%s'" % key)

## Implementation of database.MailDb base class using MongoDB as backend.
class MongoMailDb(MongoDb, database.MailDb):
	def __init__(self, database, **kwargs):
		MongoDb.__init__(self, database, **kwargs)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def append_message(self, subject, body, receiver, lifetime):
		self.save("mails", { "subject": subject,
		                     "body": body,
		                     "receiver": receiver,
		                     "created": util.now(),
		                     "lifetime": util.now() + lifetime * 1000,
		                     "sent": False })

	def get_unsent_messages(self, limit = 100):
		msgs = []
		msgs_append = msgs.append

		for m in self.find("mails", { "lifetime": { "$gte": util.now() }, "sent": False },
		                            { "_id": True, "subject": True, "body": True, "receiver": True, "created": True },
		                            sorting = [ "created", 1 ], limit = limit):
			m["id"] = str(m["_id"])
			del m["_id"]

			msgs_append(m)

		return msgs

	def mark_sent(self, id):
		self.update("mails", { "_id": ObjectId(id) }, { "$set": { "sent": True } })

## Implementation of database.RequestDb base class using MongoDB as backend.
class MongoRequestDb(MongoDb, database.RequestDb):
	def __init__(self, database, **kwargs):
		MongoDb.__init__(self, database, **kwargs)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def append_request(self, code, ip, lifetime = 3600):
		self.save("requests", { "type_id": code, "ip": ip, "lifetime": util.now() + lifetime * 1000 })

	def count_requests(self, code, ip):
		return self.count("requests", { "$and": [ { "type_id": code }, { "ip": ip }, { "lifetime": { "$gte": util.now() } } ] })

	def remove_old_requests(self):
		self.remove("requests", { "lifetime": { "$lte": util.now() } })

	def total_requests(self):
		return self.count("requests")
