# -*- coding: utf-8 -*-

import unittest, factory, util, config, app, exception, random, string, os, hashlib
from time import sleep
from exception import ErrorCode

class TestCase:
	def __cursor_to_array__(self, cur):
		a = []

		for i in cur:
			a.append(i)

		return a

	def __clear_tables__(self):
		util = factory.create_db_util()
		util.clear_tables()
		util.close()

class TestUserDb(unittest.TestCase, TestCase):
	def setUp(self):
		self.db = self.__connect_and_prepare__()

		# generate user details:
		self.user_count = 100
		self.default_text_length = 64
		self.users = self.__generate_users__(self.user_count, self.default_text_length)

		# save users in database:
		for user in self.users:
			self.db.create_user(user["name"], user["email"], user["password"], user["firstname"], user["lastname"], user["gender"])

	def tearDown(self):
		self.__clear_tables__()
		self.db.close()

	def test_00_check_user_count(self):
		self.assertEqual(self.db.count("users"), self.user_count)

	def test_01_get_users(self):
		# test if non-existing users can be found:
		for user in self.__generate_users__(10, self.default_text_length * 2):
			self.assertFalse(self.db.user_exists(user["name"]))
			self.assertIsNone(self.db.get_user(user["name"]))
			self.assertIsNone(self.db.get_user_password(user["name"]))

		# get details of each user & compare fields:
		for user in self.users:
			self.assertTrue(self.db.user_exists(user["name"]))

			# test details:
			details = self.db.get_user(user["name"])
			self.assertIsNotNone(details)
			self.__test_full_user_structure__(details)

			details = self.db.get_user_by_email(user["email"])
			self.assertIsNotNone(details)
			self.__test_full_user_structure__(details)

			for key in user:
				self.assertEqual(user[key], details[key])

			# test password:
			password = self.db.get_user_password(user["name"])
			self.assertEqual(user["password"], password)

	def test_02_block_users(self):
		for i in range(len(self.users)):
			self.users[i]["blocked"] = bool(i % 2)
			self.db.block_user(self.users[i]["name"], self.users[i]["blocked"])

		for user in self.users:
			self.assertEqual(user["blocked"], self.db.user_is_blocked(user["name"]))

	def test_03_update_users(self):
		for user in self.users:
			# update user details:
			for key in user:
				if key != "name" and key != "gender" and key != "password" and key != "avatar":
					user[key] = util.generate_junk(self.default_text_length * 2)
				elif key == "gender":
					if random.randint(0, 1) == 1:
						user["gender"] = "m"
					else:
						user["gender"] = "f"

			self.db.update_user_details(user["name"], user["email"], user["firstname"], user["lastname"], user["gender"])

			# get details from database & compare fields:
			details = self.db.get_user(user["name"])
			self.assertIsNot(details, None)

			for key in user:
				self.assertEqual(user[key], details[key])

			# update password:
			user["password"] = util.generate_junk(self.default_text_length * 2)
			self.db.update_user_password(user["name"], user["password"])

			# test if password has been changed:
			self.assertEqual(user["password"], self.db.get_user_password(user["name"]))

			# update avatar:
			user["avatar"] = util.generate_junk(self.default_text_length * 2)
			self.db.update_avatar(user["name"], user["avatar"])

			# test if avatar has been changed:
			details = self.db.get_user(user["name"])
			self.assertEqual(details["avatar"], details["avatar"])

	def test_04_email_assigned(self):
		for user in self.users:
			self.assertTrue(self.db.email_assigned(user["email"]))

		for i in range(100):
			self.assertFalse(self.db.email_assigned(util.generate_junk(self.default_text_length * 2)))

	def test_05_search_user(self):
		# search for each user:
		for user in self.users:
			queries = [ user["name"], user["firstname"], user["lastname"], user["email"] ]

			queries.append("%s %s" % (user["firstname"], user["lastname"]))
			queries.append("%s %s" % (user["lastname"], user["firstname"]))
			queries.append("%s, %s" % (user["firstname"], user["lastname"]))

			for query in queries:
				result = self.__cursor_to_array__(self.db.search_user(query))

				# test if search result contains at least one user:
				self.assertTrue(len(result) >= 1)

				# test if current user exists in search result:
				user_exists = False

				for entry in result:
					if entry["name"] == user["name"]:
						user_exists = True
						break

				self.assertTrue(user_exists)
				self.__test_user_structure__(entry)

	def test_06_user_requests(self):
		# try to find non-existing requests:
		for i in range(100):
			code = util.generate_junk(128)
			self.assertFalse(self.db.user_request_code_exists(code))
			self.assertIsNone(self.db.get_user_request(code))

		for user in self.users:
			self.assertFalse(self.db.username_requested(user["name"]))

		# create request:
		username = util.generate_junk(self.default_text_length * 2)
		email = util.generate_junk(self.default_text_length * 2)
		code = util.generate_junk(128)

		self.db.create_user_request(username, email, code, 60)

		# test created data:
		self.assertTrue(self.db.user_request_code_exists(code))

		request = self.db.get_user_request(code)
		self.assertIsNotNone(request)
		self.assertTrue(request.has_key("name"))
		self.assertTrue(request.has_key("email"))

		# remove request:
		self.db.remove_user_request(code)
		self.assertFalse(self.db.user_request_code_exists(code))

		# create new request with short lifetime:
		code = util.generate_junk(128)

		self.db.create_user_request(username, email, code, 1)
		sleep(1.5)

		# test if request still exists:
		self.assertFalse(self.db.user_request_code_exists(code))

		request = self.db.get_user_request(code)
		self.assertIsNone(request)

	def __connect_and_prepare__(self):
		db = factory.create_user_db()
		self.__clear_tables__()

		return db

	def __generate_users__(self, count, text_length = 64):
		users = []

		for i in range(count):
			users.append(self.__generate_user_details__(text_length))

		return users

	def __generate_user_details__(self, text_length):
		if random.randint(0, 1) == 1:
			gender = "m"
		else:
			gender = "f"

		return { "name": util.generate_junk(text_length),
		         "email": util.generate_junk(text_length),
		         "firstname": util.generate_junk(text_length),
		         "lastname": util.generate_junk(text_length),
		         "password": util.generate_junk(text_length),
		         "gender": gender,
		         "avatar": None }

	def __test_full_user_structure__(self, user):
		self.assertTrue(user.has_key("name"))
		self.assertTrue(user.has_key("firstname"))
		self.assertTrue(user.has_key("lastname"))
		self.assertTrue(user.has_key("email"))
		self.assertTrue(user.has_key("password"))
		self.assertTrue(user.has_key("gender"))
		self.assertTrue(user.has_key("timestamp"))
		self.assertTrue(user.has_key("avatar"))
		self.assertTrue(user.has_key("blocked"))
		self.assertTrue(user.has_key("protected"))

	def __test_user_structure__(self, user):
		self.assertTrue(user.has_key("name"))
		self.assertTrue(user.has_key("firstname"))
		self.assertTrue(user.has_key("lastname"))
		self.assertTrue(user.has_key("gender"))
		self.assertTrue(user.has_key("protected"))

class TestObjectDb(unittest.TestCase, TestCase):
	def setUp(self):
		self.db = self.__connect_and_prepare__()

	def tearDown(self):
		self.__clear_tables__()
		self.db.close()

	def test_00_create_objects(self):
		objs = self.__generate_and_store_objects__(100, 64)
		self.assertEqual(len(objs), self.db.count("objects"))

	def test_01_get_objects(self):
		# create objects:
		objs = self.__generate_and_store_objects__(100, 64)

		# test if non-existing objects can be found:
		for obj in self.__generate_objects__(10, 128):
			self.assertIsNone(self.db.get_object(obj["guid"]))
			
		# get details of each object & compare fields:
		for obj in objs:
			details = self.db.get_object(obj["guid"])
			self.assertIsNot(details, None)
			self.__test_object_structure__(details)

			for key in obj:
				self.assertEqual(obj[key], details[key])

		# delete all objects:
		self.db.remove("objects")

		# create new test records:
		objs = self.__generate_objects__(12, 64)

		for obj in objs:
			self.db.create_object(obj["guid"], obj["source"])
			sleep(0.2)

		# test paging:
		page = self.__cursor_to_array__(self.db.get_objects(0, 5))
		self.assertEqual(len(page), 5)
		self.assertEqual(objs[11]["guid"], page[0]["guid"])

		for details in page:
			self.__test_object_structure__(details)

		page = self.__cursor_to_array__(self.db.get_objects(2, 5))
		self.assertEqual(len(page), 2)
		self.assertEqual(objs[0]["guid"], page[1]["guid"])

		for details in page:
			self.__test_object_structure__(details)

	def test_02_remove_objects(self):
		objs = self.__generate_and_store_objects__(100, 64)

		# remove objects:
		for i in range(100):
			if i % 3 == 1:
				self.db.remove_object(objs[i]["guid"])

		# test object count:
		self.assertEqual(len(objs) - len(objs) / 3, self.db.count("objects"))

		# test if correct objects have been deleted:
		for i in range(100):
			if i % 3 == 1:
				deleted = True
			else:
				deleted = False

			if self.db.get_object(objs[i]["guid"]) is None:
				exists = False
			else:
				exists = True

			self.assertNotEqual(exists, deleted)

	def test_03_lock_objects(self):
		objs = self.__generate_and_store_objects__(100, 64)

		for i in range(100):
			if i % 5 == 1:
				self.db.lock_object(objs[i]["guid"], True)
			else:
				self.db.lock_object(objs[i]["guid"], False)

		for i in range(100):
			if i % 5 == 1:
				self.assertTrue(self.db.is_locked(objs[i]["guid"]))
			else:
				self.assertFalse(self.db.is_locked(objs[i]["guid"]))

	def test_04_add_tags(self):
		# create two arrays containing tags:
		tags = [ [], [] ]

		for i in range(100):
			tags[0].append(util.generate_junk(64))

			if i % 2 == 1:
				tags[1].append(util.generate_junk(128))

		# create two test objects:
		objs = self.__generate_and_store_objects__(2, 32)

		# assign each array to one object:
		for i in range(2):
			self.db.add_tags(objs[i]["guid"], tags[i])
			details = self.db.get_object(objs[i]["guid"])

			self.assertTrue(details.has_key("tags"))
			self.assertEqual(len(details["tags"]), len(tags[i]))

		# assign both arrays to first object:
		self.db.add_tags(objs[0]["guid"], tags[0])
		self.db.add_tags(objs[0]["guid"], tags[1])

		details = self.db.get_object(objs[0]["guid"])
		self.assertTrue(details.has_key("tags"))
		self.assertEqual(len(details["tags"]), len(tags[0]) + len(tags[1]))

	def test_05_tag_statistic(self):
		# create test objects:
		objs = self.__generate_and_store_objects__(5, 64)

		# insert tags:
		self.db.add_tags(objs[0]["guid"], [ "1", "2", "4", "5" ])
		self.db.add_tags(objs[1]["guid"], [ "2", "5" ])
		self.db.add_tags(objs[2]["guid"], [ "8", "6", "1" ])
		self.db.add_tags(objs[3]["guid"], [ "7", "5", "2" ])
		self.db.add_tags(objs[4]["guid"], [ "1", "2", "7", "3" ])

		# update statistic:
		self.db.build_tag_statistic()

		# get statistic:
		statistic = self.__cursor_to_array__(self.db.get_tags(2))
		self.assertIsNotNone(statistic)
		self.assertEqual(len(statistic), 2)
		self.assertEqual(statistic[0]["count"], 4)
		self.assertEqual(statistic[0]["tag"], "2")
		self.assertEqual(statistic[1]["count"], 3)
		self.assertEqual(statistic[1]["tag"], "1")

		statistic = self.__cursor_to_array__(self.db.get_tags())
		self.assertIsNotNone(statistic)
		self.assertEqual(len(statistic), 8)
		self.assertEqual(statistic[0]["count"], 4)
		self.assertEqual(statistic[0]["tag"], "2")
		self.assertEqual(statistic[1]["count"], 3)
		self.assertEqual(statistic[2]["count"], 3)
		self.assertEqual(statistic[3]["count"], 2)
		self.assertEqual(statistic[3]["tag"], "7")

		for i in range(4, 7):
			self.assertEqual(statistic[i]["count"], 1)

	def test_06_get_tagged_objects(self):
		# create test objects:
		objs = self.__generate_objects__(3, 64)

		for obj in objs:
			self.db.create_object(obj["guid"], obj["source"])
			sleep(0.2)

		# tag objects:
		self.db.add_tags(objs[0]["guid"], [ "1", "4", "5" ])
		self.db.add_tags(objs[1]["guid"], [ "3", "5", "1" ])
		self.db.add_tags(objs[2]["guid"], [ "6", "2", "1" ])

		# get objects:
		result = self.__cursor_to_array__(self.db.get_tagged_objects("1"))
		self.assertEqual(len(result), 3)
		self.assertEqual(result[0]["guid"], objs[2]["guid"])
		self.assertEqual(result[1]["guid"], objs[1]["guid"])
		self.assertEqual(result[2]["guid"], objs[0]["guid"])
		map(self.__test_object_structure__, result)

		result = self.__cursor_to_array__(self.db.get_tagged_objects("1", page = 0, page_size = 2))
		self.assertEqual(len(result), 2)
		self.assertEqual(result[0]["guid"], objs[2]["guid"])
		self.assertEqual(result[1]["guid"], objs[1]["guid"])
		map(self.__test_object_structure__, result)

		result = self.__cursor_to_array__(self.db.get_tagged_objects("1", page = 1, page_size = 2))
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["guid"], objs[0]["guid"])
		map(self.__test_object_structure__, result)

		result = self.__cursor_to_array__(self.db.get_tagged_objects("5"))
		self.assertEqual(len(result), 2)
		map(self.__test_object_structure__, result)

		result = self.__cursor_to_array__(self.db.get_tagged_objects("2"))
		self.assertEqual(len(result), 1)
		map(self.__test_object_structure__, result)

	def test_07_get_random_objects(self):
		# create test objects:
		objs = self.__generate_and_store_objects__(500 , 64)

		# get random objects:
		a = self.db.get_random_objects(100)
		self.assertEqual(len(a), 100)

		b = self.db.get_random_objects(100)
		self.assertEqual(len(b), 100)

		# test if results differ:
		count = 0

		for i in range(100):
			if a[i] == b[i]:
				count += 1

		self.assertNotEqual(count, 100)

		# try to get more random objects than possible:
		result = self.db.get_random_objects(1000)
		self.assertNotEqual(len(result), 1000)

	def test_08_favorites(self):
		# create test objects:
		objs = self.__generate_and_store_objects__(500, 32)

		# set/unset favorites:
		users = [ "a", "b", "c", "d", "e", "f", "g" ]

		for r in range(2):
			for obj in objs:
				for user in users:
					if r == 0:
						self.assertFalse(self.db.is_favorite(obj["guid"], user))

					if random.random() >= 0.5:
						fav = True
					else:
						fav = False

					self.db.favor_object(obj["guid"], user, fav)
					self.assertEqual(self.db.is_favorite(obj["guid"], user), fav)

					# test score:
					details = self.db.get_object(obj["guid"])
					self.assertEqual(details["score"]["up"] - details["score"]["down"], details["score"]["total"])

		# get favorites assigned to user:
		favs = self.__cursor_to_array__(self.db.get_favorites("h"))
		self.assertEqual(len(favs), 0)

		for i in range(10):
			self.db.favor_object(objs[i]["guid"], "h", True)

		favs = self.__cursor_to_array__(self.db.get_favorites("h"))
		self.assertEqual(len(favs), 10)

		favs = self.__cursor_to_array__(self.db.get_favorites("h", 0, 8))
		self.assertEqual(len(favs), 8)

		favs = self.__cursor_to_array__(self.db.get_favorites("h", 1, 8))
		self.assertEqual(len(favs), 2)

		for i in range(0, 10, 2):
			self.db.favor_object(objs[i]["guid"], "h", False)

		favs = self.__cursor_to_array__(self.db.get_favorites("h"))
		self.assertEqual(len(favs), 5)

		for fav in favs:
			for i in range(10):
				if fav["guid"] == objs[i]["guid"]:
					exists = True
					break
		
			if i % 2 == 0:
				self.assertFalse(exists)
			else:
				self.assertTrue(exists)

		# test sort order:
		for i in range(20):
			self.db.favor_object(objs[i]["guid"], "h", True)
			sleep(0.1)

		r = self.__cursor_to_array__(self.db.get_favorites("h", 0, 20))

		timestamp = 0

		for obj in r:
			assert obj["timestamp"] >= timestamp
			timestamp = obj["timestamp"]

	def test_09_score(self):
		# create test objects:
		objs = self.__generate_and_store_objects__(500, 32)

		# let first user rate all objects two times:
		for i in range(2):
			for i in range(500):
				self.db.rate(objs[i]["guid"], "a", True)

			# test score:
			for obj in self.db.get_objects():
				details = self.db.get_object(objs[i]["guid"])
				self.__test_object_structure__(details)
				self.assertEqual(details["score"]["total"], 1)
				self.assertEqual(details["score"]["up"], 1)
				self.assertEqual(details["score"]["down"], 0)

		# let other users rate all objects randomly:
		users = [ "b", "c", "d", "e", "f", "g" ]

		for i in range(500):
			for user in users:
				self.assertTrue(self.db.user_can_rate(objs[i]["guid"], user))

				if random.random() >= 0.5:
					self.db.rate(objs[i]["guid"], user, True)
				else:
					self.db.rate(objs[i]["guid"], user, False)

				self.assertFalse(self.db.user_can_rate(objs[i]["guid"], user))

		# test score:
		for obj in self.db.get_objects():
			self.__test_object_structure__(obj)
			self.assertEqual(obj["score"]["up"] - obj["score"]["down"], obj["score"]["total"])

		# get popular objects:
		result = self.__cursor_to_array__(self.db.get_popular_objects(0, 1000))
		self.assertEqual(len(result), 500)

		for i in range(499):
			self.__test_object_structure__(result[i])

			if i > 0:
				assert result[i]["score"]["total"] >= result[i + 1]["score"]["total"]

	def test_10_recommendations(self):
		# create test objects:
		objs = self.__generate_and_store_objects__(100, 32)

		# create recommendations:
		for i in range(100):
			if i % 2 == 0:
				self.db.recommend(objs[i]["guid"], "a", [ "b", "c" ])
			else:
				self.db.recommend(objs[i]["guid"], "b", [ "a", "c" ])

		# get recommendations:
		r = self.__cursor_to_array__(self.db.get_recommendations("c", 0, 500))
		self.assertEqual(len(r), 100)

		r = self.__cursor_to_array__(self.db.get_recommendations("a", 0, 30))
		self.assertEqual(len(r), 30)

		r = self.__cursor_to_array__(self.db.get_recommendations("a", 1, 30))
		self.assertEqual(len(r), 20)

		for user in [ "a", "b" ]:
			count = 0

			for obj in self.db.get_recommendations(user, 0, 100):
				self.__test_object_structure__(obj)

				count += 1
				flag = 0
				exists = False

				if user == "a":
					flag = 1

				for i in range(100):
					if i % 2 == flag:
						if objs[i]["guid"] == obj["guid"]:
							exists = True
							break

				self.assertTrue(exists)

			self.assertEqual(count, 50)

		# test sort order:
		for i in range(20):
			self.db.recommend(objs[i]["guid"], "a", [ "d" ])
			sleep(0.1)


		r = self.__cursor_to_array__(self.db.get_recommendations("d", 0, 20))

		timestamp = 0

		for obj in r:
			assert obj["timestamp"] >= timestamp
			timestamp = obj["timestamp"]

	def test_11_comments(self):
		# create test users:
		with factory.create_user_db() as userdb:
			userdb.create_user("a", "email-a", "first-a", "last-a", "pwd-a", "m")
			userdb.create_user("b", "email-b", "first-b", "last-b", "pwd-b", "f")

		# create test objects:
		objs = self.__generate_and_store_objects__(2, 32)

		# create comments:
		for i in range(16):
			user = "a"

			if i % 2 == 0:
				user = "b"

			guid = objs[0]["guid"]

			if i % 4 == 0:
				guid = objs[1]["guid"]

			self.db.add_comment(guid, user, util.generate_junk(256))
			sleep(0.2)

		# get comments:
		comments = self.__cursor_to_array__(self.db.get_comments(objs[0]["guid"], 0, 100))
		self.assertEqual(len(comments), 12)

		# test paging:
		comments = self.__cursor_to_array__(self.db.get_comments(objs[0]["guid"], 0, 10))
		self.assertEqual(len(comments), 10)

		comments = self.__cursor_to_array__(self.db.get_comments(objs[0]["guid"], 1, 10))
		self.assertEqual(len(comments), 2)

		comments = self.__cursor_to_array__(self.db.get_comments(objs[1]["guid"], 0, 100))
		self.assertEqual(len(comments), 4)

		# test fields:
		comment = comments[0]

		self.assertTrue(comment.has_key("timestamp"))
		self.assertTrue(comment.has_key("text"))
		self.assertTrue(comment.has_key("user"))

		user = comment["user"]

		self.assertTrue(user.has_key("name"))
		self.assertTrue(user.has_key("firstname"))
		self.assertTrue(user.has_key("lastname"))
		self.assertTrue(user.has_key("gender"))
		self.assertTrue(user.has_key("avatar"))
		self.assertTrue(user.has_key("blocked"))

	def __connect_and_prepare__(self):
		db = factory.create_object_db()
		self.__clear_tables__()

		return db

	def __generate_and_store_objects__(self, count, text_length):
		objs = self.__generate_objects__(count, text_length)

		for obj in objs:
			self.db.create_object(obj["guid"], obj["source"])

		return objs

	def __generate_objects__(self, count, text_length = 64):
		objs = []

		for i in range(count):
			objs.append(self.__generate_object__(text_length))

		return objs

	def __generate_object__(self, text_length):
		return { "guid": util.generate_junk(text_length), "source": util.generate_junk(text_length) }

	def __test_object_structure__(self, obj):
		self.assertTrue(obj.has_key("guid"))
		self.assertTrue(obj.has_key("source"))
		self.assertTrue(obj.has_key("locked"))
		self.assertTrue(obj.has_key("tags"))
		self.assertTrue(obj.has_key("score"))
		self.assertTrue(obj["score"].has_key("up"))
		self.assertTrue(obj["score"].has_key("down"))
		self.assertTrue(obj["score"].has_key("fav"))
		self.assertTrue(obj["score"].has_key("total"))
		self.assertTrue(obj.has_key("timestamp"))
		self.assertTrue(obj.has_key("comments_n"))

class TestApplication(unittest.TestCase, TestCase):
	def test_00_account_creation(self):
		with app.Application() as a:
			# generate test data:
			users = []

			user = {}
			user["username"] = util.generate_junk(8, string.ascii_letters)
			user["email"] = "test@testmail.com"
			users.append(user)

			user = {}
			user["username"] = util.generate_junk(8, string.ascii_letters)
			user["email"] = "test@test-mail.com"
			users.append(user)

			# account requests with invalid username/email:
			parameters = [ { "username": "." + util.generate_junk(64), "email": "test@testmail.com", "parameter": "username" },
				       { "username": util.generate_junk(8, string.ascii_letters), "email": util.generate_junk(64), "parameter": "email" } ]

			for p in parameters:
				err = False

				try:
					code = a.request_account(p["username"], p["email"])

				except exception.Exception, ex:
					err = self.__assert_invalid_parameter__(ex, p["parameter"])

				self.assertTrue(err)

			# check request timeout:
			code = a.request_account(users[0]["username"], users[0]["email"], 1)
			sleep(1.5)
			
			err = False

			try:
				username, email, password = a.activate_user(code)

			except exception.Exception, ex:
				err = self.__assert_error_code__(ex, ErrorCode.INVALID_REQUEST_CODE)

			self.assertTrue(err)

			# create first request & activate user:
			code = a.request_account(users[0]["username"], users[0]["email"], 60)
			username, email, password = a.activate_user(code)
			self.assertEqual(users[0]["username"], username)
			self.assertEqual(users[0]["email"], email)

			# try to create user with same username/email address:
			parameters = [ { "username": users[0]["username"], "email": users[1]["email"], "code": ErrorCode.USER_ALREADY_EXISTS },
				       { "username": users[1]["username"], "email": users[0]["email"], "code": ErrorCode.EMAIL_ALREADY_ASSIGNED } ]

			for p in parameters:
				err = False

				try:
					code = a.request_account(p["username"], p["email"])

				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			err = False

			# create second request:
			code = a.request_account(users[1]["username"], users[1]["email"])

			# try to create second account request with same username:
			err = False

			try:
				code = a.request_account(users[1]["username"], users[1]["email"])

			except exception.Exception, ex:
				err = self.__assert_error_code__(ex, ErrorCode.USERNAME_ALREADY_REQUESTED)

			self.assertTrue(err)

			# activate second user:
			username, email, password = a.activate_user(code)
			self.assertEqual(users[1]["username"], username)
			self.assertEqual(users[1]["email"], email)

			# activate user with invalid request code:
			err = False

			try:
				code = a.activate_user(util.generate_junk(64))

			except exception.Exception, ex:
				err = self.__assert_error_code__(ex, ErrorCode.INVALID_REQUEST_CODE)

			self.assertTrue(err)

	def test_01_change_password(self):
		with app.Application() as a:
			username, email, password = self.__create_account__(a, util.generate_junk(8), "test@testmail.com")
			new_password = util.generate_junk(8)

			# test invalid parameters:
			parameters = [ { "new_password": util.generate_junk(2), "username": username, "old_password": password,
					 "parameter": "new_password" },
				       { "new_password": util.generate_junk(128), "username": username, "old_password": password,
					 "parameter": "new_password" },
				       { "new_password": new_password, "username": util.generate_junk(64), "old_password": password,
					 "code": ErrorCode.COULD_NOT_FIND_USER },
				       { "new_password": new_password, "username": username, "old_password": util.generate_junk(64),
					 "code": ErrorCode.INVALID_PASSWORD } ]

			for p in parameters:
				err = False

				try:
					a.change_password(p["username"], p["old_password"], p["new_password"])
				
				except exception.Exception, ex:
					if p.has_key("parameter"):
						err = self.__assert_invalid_parameter__(ex, "new_password")
					else:
						err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			# block user:
			err = False

			with factory.create_user_db() as db:
				db.block_user(username, True)

				try:
					a.change_password(username, password, new_password)

				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, ErrorCode.USER_IS_BLOCKED)

				self.assertTrue(err)

				# reactivate user:
				db.block_user(username, False)

			# test old password:
			self.assertTrue(a.validate_password(username, password))

			# change password & test new one:
			a.change_password(username, password, new_password)
			self.assertTrue(a.validate_password(username, new_password))

	def test_02_change_user_details(self):
		with app.Application() as a:
			# create test users:
			user0 = self.__create_account__(a, "user0", "user0@testmail.com")
			user1 = self.__create_account__(a, "user1", "user1@testmail.com")

			# invalid parameters:
			parameters = [ { "firstname": util.generate_junk(128), "lastname": None, "email": "user0@testmail.com", "gender": None, "parameter": "firstname" },
				       { "firstname": None, "lastname": util.generate_junk(128), "email": "user0@testmail.com", "gender": None, "parameter": "lastname" },
				       { "firstname": None, "lastname": None, "email": util.generate_junk(128), "gender": None, "parameter": "email" },
				       { "firstname": None, "lastname": None, "email": "user0@testmail.com", "gender": "x", "parameter": "gender" } ]

			for p in parameters:
				err = False

				try:
					code = a.update_user_details("user0", p["email"], p["firstname"], p["lastname"], p["gender"])

				except exception.Exception, ex:
					err = self.__assert_invalid_parameter__(ex, p["parameter"])

				self.assertTrue(err)
		
			# use already assigned email address:
			err = False

			try:
				a.update_user_details("user0", "user1@testmail.com", None, None, None)

			except exception.Exception, ex:
				err = self.__assert_error_code__(ex, ErrorCode.EMAIL_ALREADY_ASSIGNED)

			self.assertTrue(err)

			# update user details & test result:
			a.update_user_details("user0", "test-x@testmail.com", "_firstname", "_lastname", "m")

			with factory.create_user_db() as db:
				user = db.get_user("user0")

			for key in user:
				self.assertEqual(user[key], user[key])

	def test_03_avatar(self):
		with app.Application() as a:
			self.__create_account__(a, "test-user", "test@testmail.com")

			# try to set invalid avatars:
			for image in [ "avatar00.png", "avatar01.tif" ]:
				path = os.path.join("test-data", image)

				with open(path, "rb") as f:
					err = False

					try:
						a.update_avatar("test-user", image, f)
			
					except exception.Exception, ex:
						err = self.__assert_error_code__(ex, ErrorCode.INVALID_IMAGE_FORMAT)

					self.assertTrue(err)

			# set valid avatar:
			path = os.path.join("test-data", "avatar02.jpg")
			f = open(path, "rb")
			a.update_avatar("test-user", "avatar02.jpg", f)
			f.close()

			# checksum:
			src_hash = util.hash_file(path, hashlib.md5())

			# compare file checksums:
			with factory.create_user_db() as db:
				user = db.get_user("test-user")

			path = os.path.join(config.AVATAR_DIR, user["avatar"])
			dst_hash = util.hash_file(path, hashlib.md5())

			self.assertEqual(src_hash, dst_hash)

	def test_04_get_users(self):
		with app.Application() as a:
			# create test accounts:
			self.__create_account__(a, "John.Doe", "john@testmail.com")
			self.__create_account__(a, "Martin.Smith", "martin@testmail.com")
			self.__create_account__(a, "Ada.Muster", "ada@testmail.com")

			# get user details:
			user = a.get_full_user_details("John.Doe")
			self.__test_user_details__(user)
			self.assertEqual(user["name"], "John.Doe")
			self.assertEqual(user["email"], "john@testmail.com")

			user = a.get_user_details("John.Doe")
			self.__test_user_details__(user, False)
			self.assertEqual(user["name"], "John.Doe")

			# block user & try to get details:
			with factory.create_user_db() as db:
				db.block_user("John.Doe", True)

			err = False

			try:
				details = a.get_user_details("John.Doe")

			except exception.Exception, ex:
				err = self.__assert_error_code__(ex, ErrorCode.COULD_NOT_FIND_USER)

			self.assertTrue(err)

			# find users:
			result = self.__cursor_to_array__(a.find_user("testmail"))
			self.assertEqual(len(result), 2)

			found = False
			
			for user in result:
				self.__test_user_details__(user)

				if user["name"] == "John.Doe":
					found = True
					break

			self.assertFalse(found)

			result = self.__cursor_to_array__(a.find_user("foobar"))
			self.assertEqual(len(result), 0)

	def test_05_add_tags(self):
		objs = []

		# create test objects:
		with factory.create_object_db() as db:
			for i in range(1000):
				obj = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
				db.create_object(obj["guid"], obj["source"])
				objs.append(obj)

		# get objects from database & test tags:
		with app.Application() as a:
			for i in range(1000):
				if i % 2 == 0:
					a.add_tags(objs[i]["guid"], [ "tag00", "tag01" ])
				else:
					a.add_tags(objs[i]["guid"], [ "tag02", "tag03" ])

			for obj in a.get_objects(0, 1000):
				self.assertEqual(len(obj["tags"]), 2)
				self.assertTrue("tag00" in obj["tags"] or "tag02" in obj["tags"])
				self.assertTrue("tag01" in obj["tags"] or "tag03" in obj["tags"])

			# test if tags can be added to locked objects:
			with factory.create_object_db() as db:
				for i in range(0, 1000, 3):
					db.lock_object(objs[i]["guid"], True)

			for i in range(1000):
				if i % 3 == 0:
					err = False

					try:
						a.add_tags(objs[i]["guid"], [ "tag04"])

					except exception.Exception, ex:
						err = self.__assert_error_code__(ex, ErrorCode.OBJECT_IS_LOCKED)

					self.assertTrue(err)
				else:
					a.add_tags(objs[i]["guid"], [ "tag04"])

	def test_06_get_objects(self):
		objs = []

		# create test objects:
		with factory.create_object_db() as db:
			for i in range(1000):
				obj = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
				db.create_object(obj["guid"], obj["source"])
				objs.append(obj)

		# test wrapped database functions to get objects:
		with app.Application() as a:
			for obj in objs:	
				details = a.get_object(obj["guid"])
				self.assertEqual(details["source"], obj["source"])

			result = self.__cursor_to_array__(a.get_objects(0, 100))
			self.assertEqual(len(result), 100)

			for i in range(0, 1000, 2):
				a.add_tags(objs[i]["guid"], [ "foo", "bar" ])

			result = self.__cursor_to_array__(a.get_tagged_objects("foo", 0, 1000))
			self.assertEqual(len(result), 500)

			result = self.__cursor_to_array__(a.get_random_objects(100))
			self.assertEqual(len(result), 100)

			result = self.__cursor_to_array__(a.get_popular_objects(0, 100))
			self.assertEqual(len(result), 100)

	def test_07_score(self):
		objs = []

		# create test objects:
		with factory.create_object_db() as db:
			for i in range(1000):
				obj = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
				db.create_object(obj["guid"], obj["source"])
				objs.append(obj)

		# create test accounts:
		with app.Application() as a:
			user_a = self.__create_account__(a, "user_a", "user_a@testmail.com")
			user_b = self.__create_account__(a, "user_b", "user_b@testmail.com")
			user_c = self.__create_account__(a, "user_c", "user_c@testmail.com")

			# invalid user account/object guid:
			params = [ { "username": util.generate_junk(16), "guid": objs[0]["guid"], "code": ErrorCode.COULD_NOT_FIND_USER,
			             "username": "user_a", "guid": util.generate_junk(64), "code": ErrorCode.OBJECT_NOT_FOUND } ]

			for p in params:
				err = False

				try:
					a.rate(p["username"], p["guid"], True)
			
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			# (b)locked user/object:
			with factory.create_user_db() as db:
				db.block_user("user_c")

			with factory.create_object_db() as db:
				obj = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
				db.create_object(obj["guid"], obj["source"])
				db.lock_object(obj["guid"])

			params = [ { "username": "user_c", "guid": objs[0]["guid"], "code": ErrorCode.USER_IS_BLOCKED,
			             "username": "user_a", "guid": obj["guid"], "code": ErrorCode.OBJECT_IS_LOCKED } ]

			for p in params:
				err = False

				try:
					a.rate(p["username"], p["guid"], True)
			
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			# rate:
			for obj in objs:
				for i in range(2):
					up = False

					if random.randint(0, 100) >= 20:
						up = True

					user = "user_a"

					if i == 1:
						user = "user_b"

					a.rate(user, obj["guid"], user)

			# test score:
			for obj in a.get_objects(0, 1000):
				self.assertEqual(obj["score"]["up"] - obj["score"]["down"], obj["score"]["total"])

			# try to vote two times:
			for obj in objs:
				err = False

				try:
					a.rate("user_a", obj["guid"], True)

				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, ErrorCode.USER_ALREADY_RATED)

				self.assertTrue(err)

	def test_08_favorites(self):
		objs = []

		# create test objects:
		with factory.create_object_db() as db:
			for i in range(1000):
				obj = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
				db.create_object(obj["guid"], obj["source"])
				objs.append(obj)

		# create test accounts:
		with app.Application() as a:
			user_a = self.__create_account__(a, "user_a", "user_a@testmail.com")
			user_b = self.__create_account__(a, "user_b", "user_b@testmail.com")
			user_c = self.__create_account__(a, "user_c", "user_c@testmail.com")	

			# test blocked users:
			with factory.create_user_db() as db:
				db.block_user("user_c")

			# test blocked/invalid users & invalid objects:
			params = [ { "user": "user_c", "guid": objs[0]["guid"], "code": ErrorCode.USER_IS_BLOCKED },
			           { "user": "user_d", "guid": objs[0]["guid"], "code": ErrorCode.COULD_NOT_FIND_USER },
			           { "user": "user_b", "guid": util.generate_junk(64), "code": ErrorCode.OBJECT_NOT_FOUND} ]

			for p in params:
				err = False

				try:
					a.favor(p["user"], p["guid"], True)
				
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			# create favorites:
			for obj in objs:
				a.favor("user_a", obj["guid"], True)

			for i in range(0, 1000, 2):
				a.favor("user_a", objs[i]["guid"], False)

			# get favorites:
			result = self.__cursor_to_array__(a.get_favorites("user_b"))
			self.assertEqual(len(result), 0)

			result = self.__cursor_to_array__(a.get_favorites("user_a", 0, 1000))
			self.assertEqual(len(result), 500)

			# get favorites from non-existing object:
			params = [ { "user": "user_c", "guid": objs[0]["guid"], "code": ErrorCode.USER_IS_BLOCKED },
			           { "user": "user_d", "guid": objs[0]["guid"], "code": ErrorCode.COULD_NOT_FIND_USER } ]

			for p in params:
				err = False

				try:
					a.favor(p["user"], p["guid"], True)
				
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

	def test_09_comments(self):
		# create test objects:
		with factory.create_object_db() as db:
			obj = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
			db.create_object(obj["guid"], obj["source"])

			obj_locked = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
			db.create_object(obj_locked["guid"], obj_locked["source"])
			db.lock_object(obj_locked["guid"])

		# create test accounts:
		with app.Application() as a:
			user_a = self.__create_account__(a, "user_a", "user_a@testmail.com")
			user_b = self.__create_account__(a, "user_b", "user_b@testmail.com")
			user_c = self.__create_account__(a, "user_c", "user_c@testmail.com")	

			# block user:
			with factory.create_user_db() as db:
				db.block_user("user_c")

			# test blocked/invalid users, invalid/locked objects & invalid comments:
			params = [ { "user": "user_c", "guid": obj["guid"], "comment": util.generate_junk(64), "code": ErrorCode.USER_IS_BLOCKED },
			           { "user": "user_d", "guid": obj["guid"], "comment": util.generate_junk(64), "code": ErrorCode.COULD_NOT_FIND_USER },
			           { "user": "user_b", "guid": util.generate_junk(64), "comment": util.generate_junk(64), "code": ErrorCode.OBJECT_NOT_FOUND },
			           { "user": "user_b", "guid": obj_locked["guid"], "comment": util.generate_junk(64), "code": ErrorCode.OBJECT_IS_LOCKED },
			           { "user": "user_b", "guid": obj["guid"], "comment": None, "code": ErrorCode.INVALID_PARAMETER },
			           { "user": "user_b", "guid": obj["guid"], "comment": util.generate_junk(1024), "code": ErrorCode.INVALID_PARAMETER } ]

			for p in params:
				err = False

				try:
					a.add_comment(p["guid"], p["user"], p["comment"])

				except exception.Exception, ex:
					if p["code"] == ErrorCode.INVALID_PARAMETER:
						err = self.__assert_invalid_parameter__(ex, "comment")
					else:
						err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			# create comments:
			users = [ "user_a", "user_b" ]

			for i in range(1000):
				a.add_comment(obj["guid"], users[i % 2], str(i))

			# get comments & validate order:
			result = self.__cursor_to_array__(a.get_comments(obj["guid"], 0, 5000))
			self.assertEqual(len(result), 1000)

			timestamp = 0
			i = 0

			for comment in result:
				self.assertEqual(comment["user"]["name"], users[i % 2])
				assert comment["timestamp"] >= timestamp
				self.assertEqual(str(i), comment["text"])

				timestamp = comment["timestamp"]
				i += 1

	def test_10_recommendations(self):
		objs = []

		# create test objects:
		with factory.create_object_db() as db:
			for i in range(1000):
				obj = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
				db.create_object(obj["guid"], obj["source"])
				objs.append(obj)

			obj_locked = { "guid": util.generate_junk(128), "source": util.generate_junk(128) }
			db.create_object(obj_locked["guid"], obj_locked["source"])
			db.lock_object(obj_locked["guid"])

		# create test accounts:
		with app.Application() as a:
			user_a = self.__create_account__(a, "user_a", "user_a@testmail.com")
			user_b = self.__create_account__(a, "user_b", "user_b@testmail.com")
			user_c = self.__create_account__(a, "user_c", "user_c@testmail.com")	
			user_d = self.__create_account__(a, "user_d", "user_d@testmail.com")	

		# block account:
		with factory.create_user_db() as db:
			db.block_user("user_d")

		with app.Application() as a:
			# create recommendations:
			for obj in objs:
				a.recommend("user_a", obj["guid"], [ "user_a", "user_b", "user_c" ])
				a.recommend("user_b", obj["guid"], [ "user_c", "foo", "user_d" ])

			# get recommendations:
			result = self.__cursor_to_array__(a.get_recommendations("user_a", 0, 5000))
			self.assertEqual(len(result), 0)

			result = self.__cursor_to_array__(a.get_recommendations("user_b", 0, 5000))
			self.assertEqual(len(result), 1000)

			result = self.__cursor_to_array__(a.get_recommendations("user_c", 0, 5000))
			self.assertEqual(len(result), 1000)

			# test invalid & blocked users:
			params = [ { "username": "user_d", "guid": objs[0]["guid"], "code": ErrorCode.USER_IS_BLOCKED },
			           { "username": "foo", "guid": objs[0]["guid"], "code": ErrorCode.COULD_NOT_FIND_USER },
			           { "username": "user_a", "guid": util.generate_junk(64), "code": ErrorCode.OBJECT_NOT_FOUND }]

			for p in params:
				err = False

				try:
					a.recommend(p["username"], p["guid"], [ "user_a", "user_b", "user_c" ])
			
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			params = [ { "username": "user_d", "code": ErrorCode.USER_IS_BLOCKED },
			           { "username": "foo", "code": ErrorCode.COULD_NOT_FIND_USER } ]


			for p in params:
				err = False

				try:
					a.get_recommendations(p["username"])
			
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

	def setUp(self):
		self.__clear_tables__()
		util.remove_all_files(config.AVATAR_DIR)

	def tearDown(self):
		self.__clear_tables__()
		util.remove_all_files(config.AVATAR_DIR)

	def __create_account__(self, app, username, email):
		code = app.request_account(username, email)

		return app.activate_user(code)

	def __assert_invalid_parameter__(self, ex, parameter):
		self.assertEqual(ex.code, ErrorCode.INVALID_PARAMETER)
		self.assertEqual(ex.parameter, parameter)

		return True

	def __assert_error_code__(self, ex, code):
		self.assertEqual(ex.code, code)

		return True

	def __test_user_details__(self, user, with_email = True):
		self.assertTrue(user.has_key("name"))
		self.assertTrue(user.has_key("firstname"))
		self.assertTrue(user.has_key("lastname"))
		self.assertEqual(user.has_key("email"), with_email)
		self.assertFalse(user.has_key("password"))
		self.assertTrue(user.has_key("gender"))
		self.assertTrue(user.has_key("timestamp"))
		self.assertTrue(user.has_key("avatar"))
		self.assertFalse(user.has_key("blocked"))
		self.assertTrue(user.has_key("protected"))

		return True

def run_test_case(case):
	suite = unittest.TestLoader().loadTestsFromTestCase(case)
	unittest.TextTestRunner(verbosity = 2).run(suite)

if __name__ == "__main__":
	for case in [ TestUserDb, TestObjectDb, TestApplication ]:
		run_test_case(case)
