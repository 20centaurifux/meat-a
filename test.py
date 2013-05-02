#-*- coding: utf-8 -*-
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

import unittest, random, string, os, hashlib, re, json
import factory, util, config, app, client, exception
from time import sleep
from exception import ErrorCode
from database import StreamDb, RequestDb

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
			self.db.create_user(user["name"], user["email"], user["password"], user["firstname"], user["lastname"], user["gender"], user["language"], user["protected"])

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

					user["protected"] = bool(random.randint(0, 1))

			self.db.update_user_details(user["name"], user["email"], user["firstname"], user["lastname"], user["gender"], user["language"], user["protected"])

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

			# request new password:
			code = util.generate_junk(128)
			self.assertFalse(self.db.password_request_code_exists(code))

			self.db.create_password_request(user["name"], code, 60)
			self.assertTrue(self.db.password_request_code_exists(code))

			username = self.db.get_password_request(code)
			self.assertEqual(username, user["name"])

			self.db.remove_password_request(code)
			self.assertFalse(self.db.password_request_code_exists(code))

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

	def test_07_friendship(self):
		users_a = self.users[:50]
		users_b = self.users[50:]

		for i in range(50):
			self.assertFalse(self.db.is_following(users_a[i]["name"], users_b[i]["name"]))
			self.assertFalse(self.db.is_following(users_b[i]["name"], users_a[i]["name"]))

			self.db.follow(users_a[i]["name"], users_b[i]["name"])
			self.assertTrue(self.db.is_following(users_a[i]["name"], users_b[i]["name"]))
			self.assertFalse(self.db.is_following(users_b[i]["name"], users_a[i]["name"]))

			self.db.follow(users_b[i]["name"], users_a[i]["name"])
			self.assertTrue(self.db.is_following(users_a[i]["name"], users_b[i]["name"]))
			self.assertTrue(self.db.is_following(users_b[i]["name"], users_a[i]["name"]))

			self.db.follow(users_a[i]["name"], users_b[i]["name"], False)
			self.assertFalse(self.db.is_following(users_a[i]["name"], users_b[i]["name"]))
			self.assertTrue(self.db.is_following(users_b[i]["name"], users_a[i]["name"]))

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
		         "language": util.generate_junk(text_length),
		         "protected": True,
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
		self.assertTrue(user.has_key("language"))
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
			self.assertFalse(self.db.object_exists(obj["guid"]))
			
		# get details of each object & compare fields:
		for obj in objs:
			details = self.db.get_object(obj["guid"])
			self.assertIsNot(details, None)
			self.__test_object_structure__(details)
			self.assertTrue(self.db.object_exists(obj["guid"]))

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
				self.assertEqual(exists, self.db.recommendation_exists(objs[i]["guid"], user))

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

class TestStreamDb(unittest.TestCase, TestCase):
	def test_00_recommendations(self):
		# generate test data:
		recommendations = {}

		for i in range(333):
			if i % 7 == 0:
				comment = None
			else:
				comment = util.generate_junk(128)

			data = {}

			data["comment"] = comment

			if i % 3 == 0:
				data["sender"] = "user_b"
				data["receiver"] = "user_a"
			else:
				data["sender"] = "user_a"
				data["receiver"] = "user_b"

			recommendations[util.generate_junk(64)] = data

		with factory.create_stream_db() as db:
			# create messages:
			i = 0

			for guid, data in recommendations.items():
				db.add_message(StreamDb.MessageType.RECOMMENDATION, data["sender"], data["receiver"], guid = guid, comment = data["comment"])

				if i % 33 == 0:
					sleep(0.1)

				i += 1

			# get & validate messages:
			self.__validate_messages__(db, 111, 222, self.__test_recommendation__)

			with factory.create_stream_db() as db:
				for msg in db.get_messages("user_a"):
					if recommendations[msg["guid"]].has_key("comment"):
						self.assertTrue(msg.has_key("comment"))

	def test_01_comments(self):
		# generate test data:
		comments = {}

		for i in range(500):
			data = {}

			data["comment"] = util.generate_junk(128)

			if i % 5 == 0:
				data["sender"] = "user_b"
				data["receiver"] = "user_a"
			else:
				data["sender"] = "user_a"
				data["receiver"] = "user_b"

			comments[util.generate_junk(64)] = data

		with factory.create_stream_db() as db:
			# create messages:
			i = 0

			for guid, data in comments.items():
				db.add_message(StreamDb.MessageType.COMMENT, data["sender"], data["receiver"], guid = guid, comment = data["comment"])

				if i % 25 == 0:
					sleep(0.1)

				i += 1

			# get & validate messages:
			self.__validate_messages__(db, 100, 400, self.__test_comment__)

	def test_02_favor(self):
		# generate test data:
		favorites = {}

		for i in range(777):
			data = {}

			if i % 7 == 0:
				data["sender"] = "user_b"
				data["receiver"] = "user_a"
			else:
				data["sender"] = "user_a"
				data["receiver"] = "user_b"

			favorites[util.generate_junk(64)] = data

		with factory.create_stream_db() as db:
			# create messages:
			i = 0

			for guid, data in favorites.items():
				db.add_message(StreamDb.MessageType.FAVOR, data["sender"], data["receiver"], guid = guid)

				if i % 25 == 0:
					sleep(0.1)

				i += 1

			# get & validate messages:
			self.__validate_messages__(db, 111, 666, self.__test_favor__)

	def test_03_votes(self):
		# generate test data:
		votes = {}

		for i in range(600):
			data = {}

			if i % 6 == 0:
				data["sender"] = "user_b"
				data["receiver"] = "user_a"
			else:
				data["sender"] = "user_a"
				data["receiver"] = "user_b"

			if i % 3 == 0:
				data["up"] = True
			else:
				data["up"] = False

			votes[util.generate_junk(64)] = data

		with factory.create_stream_db() as db:
			# create messages:
			i = 0

			for guid, data in votes.items():
				db.add_message(StreamDb.MessageType.VOTE, data["sender"], data["receiver"], guid = guid, up = data["up"])

				if i % 30 == 0:
					sleep(0.1)

				i += 1

			# get & validate messages:
			self.__validate_messages__(db, 100, 500, self.__test_vote__)

			with factory.create_stream_db() as db:
				for msg in db.get_messages("user_a"):
					self.assertEqual(votes[msg["guid"]]["up"], msg["up"])

	def setUp(self):
		self.__clear_tables__()

		# create test users:
		with factory.create_user_db() as db:
			db.create_user("user_a", "user_a@testmail.com", util.generate_junk(64), util.generate_junk(64), util.generate_junk(64), "m", True)
			db.create_user("user_b", "user_b@testmail.com", util.generate_junk(64), util.generate_junk(64), util.generate_junk(64), "f", False)

	def tearDown(self):
		self.__clear_tables__()

	def __test_order__(self, stream):
		timestamp = -1

		for msg in stream:
			if timestamp == -1:
				timestamp = msg["timestamp"]
			else:
				assert msg["timestamp"] <= timestamp
				timestamp = msg["timestamp"]

	def __find_test_timestamp__(self, messages):
		i = int(len(messages) / 1.5)
		timestamp = messages[i]["timestamp"]

		while messages[i]["timestamp"] == timestamp:
			i += 1

		return i, messages[i]["timestamp"]

	def __test_message__(self, msg, code, sender, receiver):
		self.assertEqual(msg["type_id"], code)
		self.assertEqual(msg["sender"]["name"], sender)
		self.assertTrue(msg["sender"].has_key("firstname"))
		self.assertTrue(msg["sender"].has_key("lastname"))
		self.assertTrue(msg["sender"].has_key("avatar"))
		self.assertTrue(msg["sender"].has_key("blocked"))
		self.assertTrue(msg["sender"].has_key("gender"))
		self.assertEqual(msg["receiver"], receiver)
		self.assertTrue(msg.has_key("timestamp"))

	def __test_messages__(self, messages, sender, receiver, validator):
		for msg in messages:
			validator(msg, sender, receiver)

		self.__test_order__(messages)

	def __validate_messages__(self, db, len_a, len_b, validator):
		result = self.__cursor_to_array__(db.get_messages("user_a", len_a * 2))
		self.assertEqual(len(result), len_a)
		self.__test_messages__(result, "user_b", "user_a", validator)

		result = self.__cursor_to_array__(db.get_messages("user_b", len_a / 2))
		self.assertEqual(len(result), len_a / 2)

		result = self.__cursor_to_array__(db.get_messages("user_b", len_b * 2))
		self.assertEqual(len(result), len_b)
		self.__test_messages__(result, "user_a", "user_b", validator)

		index, timestamp = self.__find_test_timestamp__(result)
		length = len_b - index

		count = len(result)

		result = self.__cursor_to_array__(db.get_messages("user_b", len_b, timestamp))
		self.assertEqual(count - index, len(result))

	def __test_recommendation__(self, r, sender, receiver):
		self.__test_message__(r, StreamDb.MessageType.RECOMMENDATION, sender, receiver)
		self.assertTrue(r.has_key("guid"))

	def __test_comment__(self, v, sender, receiver):
		self.__test_message__(v, StreamDb.MessageType.COMMENT, sender, receiver)
		self.assertTrue(v.has_key("guid"))
		self.assertTrue(v.has_key("comment"))

	def __test_favor__(self, f, sender, receiver):
		self.__test_message__(f, StreamDb.MessageType.FAVOR, sender, receiver)

	def __test_vote__(self, v, sender, receiver):
		self.__test_message__(v, StreamDb.MessageType.VOTE, sender, receiver)
		self.assertTrue(v.has_key("guid"))
		self.assertTrue(v.has_key("up"))

class TestMailDb(unittest.TestCase, TestCase):
	def test_00_mails(self):
		with factory.create_mail_db() as db:
			# create test messages:
			for i in range(1000):
				db.append_message("subject-%d" % i, "body-%d" % i, "test@testmail.com", 120)

			# get & validate messages:
			result = self.__cursor_to_array__(db.get_unsent_messages(10))
			self.assertEqual(len(result), 10)

			result = self.__cursor_to_array__(db.get_unsent_messages(5000))
			self.assertEqual(len(result), 1000)

			i = 0
			created = 0

			reg_subject = re.compile("^subject-[\d]{1,3}$")
			reg_body = re.compile("^body-[\d]{1,3}$")

			for msg in result:
				self.assertIsNotNone(msg["id"])
				self.assertIsNotNone(reg_subject.match(msg["subject"]))
				self.assertIsNotNone(reg_body.match(msg["body"]))
				self.assertEqual(msg["receiver"], "test@testmail.com")
				assert msg["created"] >= created

				created = msg["created"]
				i += 1

				# mark message as sent:
				db.mark_sent(msg["id"])

			result = self.__cursor_to_array__(db.get_unsent_messages(5000))
			self.assertEqual(len(result), 0)

			# test lifetime:
			db.append_message("foo", "bar", "test@testmail.com", 1)
			sleep(1.5)

			result = self.__cursor_to_array__(db.get_unsent_messages())
			self.assertEqual(len(result), 0)

	def setUp(self):
		self.__clear_tables__()

	def tearDown(self):
		self.__clear_tables__()

class TestRequestDb(unittest.TestCase, TestCase):
	def test_00_requests(self):
		with factory.create_request_db() as db:
			# append a single request & test lifetime:
			db.append_request(RequestDb.RequestType.ACCOUNT_REQUEST, "127.0.0.1", 1)
			sleep(1.5)

			self.assertEqual(db.count_requests(RequestDb.RequestType.ACCOUNT_REQUEST, "127.0.0.1"), 0)
			self.assertEqual(db.total_requests(), 1)

			db.remove_old_requests()

			self.assertEqual(db.total_requests(), 0)

			# insert multiple requests:
			for i in range(1000):
				if i % 2 == 0:
					ip = "127.0.0.1"
				else:
					ip = "192.168.1.1"

				if i % 5 == 0:
					code = RequestDb.RequestType.ACCOUNT_REQUEST
				else:
					code = RequestDb.RequestType.PASSWORD_RESET

				db.append_request(code, ip)
	
			self.assertEqual(db.count_requests(RequestDb.RequestType.ACCOUNT_REQUEST, "127.0.0.1"), 100)
			self.assertEqual(db.count_requests(RequestDb.RequestType.PASSWORD_RESET, "127.0.0.1"), 400)

			self.assertEqual(db.count_requests(RequestDb.RequestType.ACCOUNT_REQUEST, "192.168.1.1"), 100)
			self.assertEqual(db.count_requests(RequestDb.RequestType.PASSWORD_RESET, "192.168.1.1"), 400)

			self.assertEqual(db.count_requests(RequestDb.RequestType.PASSWORD_RESET, "255.255.255.0"), 0)

	def setUp(self):
		self.__clear_tables__()

	def tearDown(self):
		self.__clear_tables__()

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

			# blocked user:
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

			# change password using request code:
			code = a.request_password(username, email)
			name, addr, password = a.generate_password(code)

			self.assertEqual(addr, email)
			self.assertEqual(name, username)
			self.assertTrue(a.validate_password(username, password))

			# test invalid parameters:
			parameters = [ { "username": username, "email": email, "timeout": 60, "code": ErrorCode.INVALID_REQUEST_CODE },
			               { "username": util.generate_junk(16), "email": email, "timeout": 60, "code": ErrorCode.COULD_NOT_FIND_USER },
			               { "username": username, "email": util.generate_junk(16), "timeout": 1, "code": ErrorCode.INVALID_EMAIL_ADDRESS },
			               { "username": username, "email": email, "timeout": 1, "code": ErrorCode.INVALID_REQUEST_CODE } ]

			for p in parameters:
				err = False

				try:
					code = a.request_password(p["username"], p["email"], p["timeout"])
					sleep(1.1)

					if p.has_key("code"):
						code = p["code"]

					name, addr, password = a.generate_password(code)
				
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

	def test_02_change_user_details(self):
		with app.Application() as a:
			# create test users:
			user0 = self.__create_account__(a, "user0", "user0@testmail.com")
			user1 = self.__create_account__(a, "user1", "user1@testmail.com")

			# invalid parameters:
			parameters = [ { "firstname": util.generate_junk(128), "lastname": None, "email": "user0@testmail.com", "gender": None, "language": "en", "protected": False, "parameter": "firstname" },
				       { "firstname": None, "lastname": util.generate_junk(128), "email": "user0@testmail.com", "gender": None, "language": "en", "protected": False, "parameter": "lastname" },
				       { "firstname": None, "lastname": None, "email": util.generate_junk(128), "gender": None, "language": "en", "protected": False, "parameter": "email" },
				       { "firstname": None, "lastname": None, "email": "user0@testmail.com", "gender": "x", "language": "en", "protected": False, "parameter": "gender" },
				       { "firstname": None, "lastname": None, "email": "user0@testmail.com", "gender": "m", "language": "en", "protected": None, "parameter": "protected" },
				       { "firstname": None, "lastname": None, "email": "user0@testmail.com", "gender": "m", "language": util.generate_junk(8), "protected": True, "parameter": "language" } ]

			for p in parameters:
				err = False

				try:
					code = a.update_user_details("user0", p["email"], p["firstname"], p["lastname"], p["gender"], p["language"], p["protected"])

				except exception.Exception, ex:
					err = self.__assert_invalid_parameter__(ex, p["parameter"])

				self.assertTrue(err)
		
			# use already assigned email address:
			err = False

			try:
				a.update_user_details("user0", "user1@testmail.com", None, None, None, "en", True)

			except exception.Exception, ex:
				err = self.__assert_error_code__(ex, ErrorCode.EMAIL_ALREADY_ASSIGNED)

			self.assertTrue(err)

			# update user details & test result:
			a.update_user_details("user0", "test-x@testmail.com", "_firstname", "_lastname", "f", "en", False)

			with factory.create_user_db() as db:
				user = db.get_user("user0")

			self.assertEqual(user["name"], "user0")
			self.assertEqual(user["email"], "test-x@testmail.com")
			self.assertEqual(user["firstname"], "_firstname")
			self.assertEqual(user["lastname"], "_lastname")
			self.assertEqual(user["gender"], "f")
			self.assertFalse(user["protected"])

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

			# block user & try to get details:
			a.disable_user("John.Doe")

			err = False

			try:
				details = a.get_full_user_details("John.Doe")

			except exception.Exception, ex:
				err = self.__assert_error_code__(ex, ErrorCode.COULD_NOT_FIND_USER)

			self.assertTrue(err)

			# get user details respecting friendship:
			a.update_user_details("Ada.Muster", "ada@testmail.com", None, None, "f", "en", False)
			details = a.get_user_details("Martin.Smith", "Ada.Muster")
			self.__test_user_details__(details, with_language = False)

			a.update_user_details("Ada.Muster", "ada@testmail.com", None, None, "f", "en", True)
			details = a.get_user_details("Martin.Smith", "Ada.Muster")
			self.__test_user_details__(details, False, False, False, False)

			a.follow("Martin.Smith", "Ada.Muster")
			details = a.get_user_details("Martin.Smith", "Ada.Muster")
			self.__test_user_details__(details, False, False, False, False)

			a.follow("Ada.Muster", "Martin.Smith")
			details = a.get_user_details("Martin.Smith", "Ada.Muster")
			self.__test_user_details__(details, with_language = False)

			params = [ { "user1": "John.Doe", "user2": "Ada.Muster", "code": ErrorCode.USER_IS_BLOCKED,
			             "user1": "Martin.Smith", "user2": "John.Doe", "code": ErrorCode.USER_IS_BLOCKED,
			             "user1": "Martin.Smith", "user2": util.generate_junk(16), "code": ErrorCode.COULD_NOT_FIND_USER,
			             "user1": util.generate_junk(16), "user2": "Ada.Muster", "code": ErrorCode.COULD_NOT_FIND_USER } ]

			for p in params:
				err = False

				try:
					a.follow(p["user1"], p["user2"])
			
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			# get own user profile:
			details = a.get_user_details("Ada.Muster", "Ada.Muster")
			self.__test_user_details__(details, with_password = True)
			self.assertTrue(details.has_key("password"))

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
			# create test accounts:
			user_a = self.__create_account__(a, "user_a", "usera@testmail.com")
			user_b = self.__create_account__(a, "user_b", "userb@testmail.com")

			a.disable_user("user_b")

			for i in range(1000):
				if i % 2 == 0:
					a.add_tags("user_a", objs[i]["guid"], [ "tag00", "tag01" ])
				else:
					a.add_tags("user_a", objs[i]["guid"], [ "tag02", "tag03" ])

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
						a.add_tags("user_a", objs[i]["guid"], [ "tag04"])

					except exception.Exception, ex:
						err = self.__assert_error_code__(ex, ErrorCode.OBJECT_IS_LOCKED)

					self.assertTrue(err)
				else:
					a.add_tags("user_a", objs[i]["guid"], [ "tag04"])

			# invalid accounts:
			params = [ { "username": util.generate_junk(16), "tags": [ "foo" ], "code": ErrorCode.COULD_NOT_FIND_USER,
			             "username": "user_b", "tags": [ "foo" ], "code": ErrorCode.USER_IS_BLOCKED,
			             "username": "user_b", "tags": [ "f" ], "code": ErrorCode.INVALID_PARAMETER,
			             "username": "user_b", "tags": [ util.generate_junk(128) ], "code": ErrorCode.INVALID_PARAMETER } ]

			for p in params:
				err = False

				try:
					a.add_tags(p["username"], objs[0]["guid"], "foo")

				except exception.Exception, ex:
					if p["code"] == ErrorCode.INVALID_PARAMETER:
						err = self.__assert_invalid_parameter__(ex, "tag")
					else:
						err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

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
			self.__create_account__(a, "user_a", "user_a@testmail.com")

			for obj in objs:	
				details = a.get_object(obj["guid"])
				self.assertEqual(details["source"], obj["source"])

			result = self.__cursor_to_array__(a.get_objects(0, 100))
			self.assertEqual(len(result), 100)

			for i in range(0, 1000, 2):
				a.add_tags("user_a", objs[i]["guid"], [ "foo", "bar" ])

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

			# create friendship
			a.follow("user_a", "user_b")
			a.follow("user_b", "user_a")
			a.follow("user_b", "user_c")

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
			a.disable_user("user_c")

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

			# get & validete messages:
			result = self.__cursor_to_array__(a.get_messages("user_a", 5000))
			self.assertEqual(len(result), 1001)

			result = self.__cursor_to_array__(a.get_messages("user_b", 5000))
			self.assertEqual(len(result), 1001)

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

			# friendship:
			a.follow("user_a", "user_b")
			a.follow("user_a", "user_c")
			a.follow("user_b", "user_a")

			# test blocked users:
			a.disable_user("user_c")

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

			# get & validete messages:
			result = self.__cursor_to_array__(a.get_messages("user_a", 5000))
			self.assertEqual(len(result), 1)

			result = self.__cursor_to_array__(a.get_messages("user_b", 5000))
			self.assertEqual(len(result), 1001)

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

			# create friendship:
			a.follow("user_a", "user_b")
			a.follow("user_b", "user_a")
			a.follow("user_b", "user_c")

			# block user:
			a.disable_user("user_c")

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

			# get & validate messages:
			result = self.__cursor_to_array__(a.get_messages("user_a", 5000))
			self.assertEqual(len(result), 501)

			result = self.__cursor_to_array__(a.get_messages("user_b", 5000))
			self.assertEqual(len(result), 501)

	def test_10_friendship(self):
		with app.Application() as a:
			# create test users:
			self.__create_account__(a, "John.Doe", "john@testmail.com")
			self.__create_account__(a, "Martin.Smith", "martin@testmail.com")
			self.__create_account__(a, "Ada.Muster", "ada@testmail.com")

			# invalid parameters:
			a.disable_user("John.Doe")

			params = [ { "user1": "John.Doe", "user2": "Ada.Muster", "code": ErrorCode.USER_IS_BLOCKED,
			             "user1": "Martin.Smith", "user2": "John.Doe", "code": ErrorCode.USER_IS_BLOCKED,
			             "user1": "Martin.Smith", "user2": util.generate_junk(16), "code": ErrorCode.COULD_NOT_FIND_USER } ]

			for p in params:
				err = False

				try:
					a.follow(p["user1"], p["user2"])
			
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			# create friendship:
			params = [ { "user1": "Martin.Smith", "user2": "Ada.Muster" }, { "user1": "Ada.Muster", "user2": "Martin.Smith" } ]

			for p in params:
				a.follow(p["user1"], p["user2"])
				self.assertTrue(a.is_following(p["user1"], p["user2"]))

			a.follow("Martin.Smith", "Ada.Muster", False)
			self.assertFalse(a.is_following("Martin.Smith", "Ada.Muster"))
			self.assertTrue(a.is_following("Ada.Muster", "Martin.Smith"))

			# get & validate messages:
			messages = self.__cursor_to_array__(a.get_messages("Martin.Smith"))
			self.assertEqual(len(messages), 1)

			messages = self.__cursor_to_array__(a.get_messages("Ada.Muster"))
			self.assertEqual(len(messages), 2)

	def test_11_recommendations(self):
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
			a.disable_user("user_d")

			# create friendship:
			a.follow("user_a", "user_c")
			a.follow("user_c", "user_a")

			# create recommendations:
			for obj in objs:
				a.recommend("user_a", obj["guid"], [ "user_a", "user_b", "user_c" ])
				a.recommend("user_b", obj["guid"], [ "user_c", "foo", "user_d" ])

			# get recommendations & messages:
			result = self.__cursor_to_array__(a.get_recommendations("user_a", 0, 5000))
			self.assertEqual(len(result), 0)

			result = self.__cursor_to_array__(a.get_messages("user_a", 5000))
			self.assertEqual(len(result), 1)

			result = self.__cursor_to_array__(a.get_recommendations("user_b", 0, 5000))
			self.assertEqual(len(result), 0)

			result = self.__cursor_to_array__(a.get_messages("user_b", 5000))
			self.assertEqual(len(result), 0)

			result = self.__cursor_to_array__(a.get_recommendations("user_c", 0, 5000))
			self.assertEqual(len(result), 1000)

			result = self.__cursor_to_array__(a.get_messages("user_c", 5000))
			self.assertEqual(len(result), 1001)

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

	def test_12_find_users(self):
		with app.Application() as a:
			# create test accounts:
			for c in [ "a", "b", "c", "d", "e" ]:
				self.__create_account__(a, "user_%s" % c, "user_%s@testmail.com" % c)

			# create friendship:
			a.follow("user_a", "user_b")
			a.follow("user_b", "user_a")

			# make user profile public:
			a.update_user_details("user_d", "user_d@testmail.com", None, None, None, "en", False)

			# block user:
			a.disable_user("user_e")

			# search users:
			result = self.__cursor_to_array__(a.find_user("user_a", "user"))
			self.assertEqual(len(result), 3)

			for user in result:
				if user["name"] == "user_b" or user["name"] == "user_d":
					self.__test_user_details__(user, with_language = False)
				elif user["name"] == "user_c":
					self.__test_user_details__(user, False, False, False, False)

	def test_13_messages(self):
		with app.Application() as a:
			# create test accounts:
			self.__create_account__(a, "John.Doe", "john@testmail.com")
			self.__create_account__(a, "Martin.Smith", "martin@testmail.com")

			# block user:
			a.disable_user("John.Doe")

			# invalid parameters:
			params = [ { "username": "John.Doe", "code": ErrorCode.USER_IS_BLOCKED },
			           { "username": util.generate_junk(16), "code": ErrorCode.COULD_NOT_FIND_USER } ]

			for p in params:
				err = False

				try:
					a.get_messages(p["username"])
			
				except exception.Exception, ex:
					err = self.__assert_error_code__(ex, p["code"])

				self.assertTrue(err)

			with factory.create_stream_db() as db:
				for i in range(500):
					db.add_message(StreamDb.MessageType.RECOMMENDATION, "John.Doe", "Martin.Smith", guid = util.generate_junk(128))

			result = self.__cursor_to_array__(a.get_messages("Martin.Smith", 5))
			self.assertEqual(len(result), 5)

			result = self.__cursor_to_array__(a.get_messages("Martin.Smith", 1000))
			self.assertEqual(len(result), 500)

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

	def __test_user_details__(self, user, with_email = True, with_following = True, with_password = False, with_language = True):
		self.assertTrue(user.has_key("name"))
		self.assertTrue(user.has_key("firstname"))
		self.assertTrue(user.has_key("lastname"))
		self.assertEqual(user.has_key("email"), with_email)
		self.assertEqual(user.has_key("following"), with_following)
		self.assertEqual(user.has_key("password"), with_password)
		self.assertTrue(user.has_key("gender"))
		self.assertTrue(user.has_key("timestamp"))
		self.assertTrue(user.has_key("avatar"))
		self.assertFalse(user.has_key("blocked"))
		self.assertEqual(user.has_key("language"), with_language)
		self.assertTrue(user.has_key("protected"))

		return True

class TestAuthenticatedApplication(unittest.TestCase, TestCase):
	def test_00_user_functions(self):
		with app.AuthenticatedApplication() as a:
			# change password:
			new_password = util.generate_junk(16)
			self.__test_method__(a.change_password, "user_a", old_password = self.__users["user_a"]["password"], new_password = new_password)
			self.__test_failed_method__(a.change_password, "user_a", ErrorCode.AUTHENTICATION_FAILED,
			                            old_password = self.__users["user_a"]["password"], new_password = new_password)

			self.__users["user_a"]["password"] = new_password

			# update user details:
			self.__test_method__(a.update_user_details, "user_a", email = "_user_a@testmail.com", firstname = "first_a", lastname = "last_a",
			                     gender = "m", language = "en", protected = False)

			# get user details:
			details = self.__test_method__(a.get_user_details, "user_a", name = "user_a")

			self.assertEqual(details["name"], "user_a")
			self.assertEqual(details["email"], "_user_a@testmail.com")
			self.assertEqual(details["firstname"], "first_a")
			self.assertEqual(details["lastname"], "last_a")
			self.assertEqual(details["gender"], "m")
			self.assertEqual(details["language"], "en")
			self.assertFalse(details["protected"])
			self.assertEqual(details["password"], util.hash(new_password))
			self.assertIsNone(details["avatar"])

			details = self.__test_method__(a.get_user_details, "user_a", name = "user_b")
			self.assertEqual(details["name"], "user_b")
			self.assertFalse(details.has_key("language"))
			self.assertFalse(details.has_key("password"))
			self.assertFalse(details.has_key("email"))

			# update avatar:
			path = os.path.join("test-data", "avatar02.jpg")
			with open(path, "rb") as f:
				req = self.__create_signature__("user_a", new_password, filename = "avatar02.jpg")
				a.update_avatar(req, "avatar02.jpg", f)

			details = self.__test_method__(a.get_user_details, "user_a", name = "user_a")
			self.assertIsNotNone(details["avatar"])

			# find users:
			result = self.__cursor_to_array__(self.__test_method__(a.find_user, "user_a", query = "test"))
			self.assertEqual(len(result), 2)

	def test_01_object_functions(self):
		# create test objects:
		objs = []

		with factory.create_object_db() as db:
			for i in range(100):
				obj = { "guid": util.generate_junk(64), "source": util.generate_junk(128) }
				objs.append(obj)
				db.create_object(obj["guid"], obj["source"])

		
		with app.AuthenticatedApplication() as a:
			# get objects:
			for obj in objs:
				details = self.__test_method__(a.get_object, "user_a", guid = obj["guid"])
				self.assertEqual(obj["source"], details["source"])

			result = self.__cursor_to_array__(self.__test_method__(a.get_objects, "user_a", page = 1, page_size = 80))
			self.assertEqual(len(result), 20)

			# tags:
			for i in range(50):
				self.__test_method__(a.add_tags, "user_a", guid = objs[i]["guid"], tags = [ "foo", "bar"])

			result = self.__cursor_to_array__(self.__test_method__(a.get_tagged_objects, "user_a", tag = "foo", page = 1, page_size = 40))
			self.assertEqual(len(result), 10)

			for obj in result:
				assert "foo" in obj["tags"]

			# random objects:
			result = self.__cursor_to_array__(self.__test_method__(a.get_random_objects, "user_a", page_size = 25))
			self.assertEqual(len(result), 25)

			# score:
			for obj in objs:
				for i in range(2):
					up = False

					if random.randint(0, 1) == 1:
						up = True

					user = "user_a"

					if i == 1:
						user = "user_b"

					self.__test_method__(a.rate, user, guid = obj["guid"], up = up)

			result = self.__cursor_to_array__(self.__test_method__(a.get_popular_objects, "user_a", page = 0, page_size = 500))
			self.assertEqual(len(result), 100)

			for i in range(99):
				assert result[i]["score"]["total"] >= result[i + 1]["score"]["total"]

			# favorites:
			for i in range(100):
				user = "user_a"

				if i % 2 == 0:
					user = "user_b"

				self.__test_method__(a.favor, user, guid = objs[i]["guid"], favor = True)

			result = self.__cursor_to_array__(self.__test_method__(a.get_favorites, "user_a", page = 0, page_size = 500))
			self.assertEqual(len(result), 50)

			for obj in result[25:]:
				self.__test_method__(a.favor, user, guid = obj["guid"], favor = False)

			result = self.__cursor_to_array__(self.__test_method__(a.get_favorites, "user_a", page = 0, page_size = 500))
			self.assertEqual(len(result), 25)

			result = self.__cursor_to_array__(self.__test_method__(a.get_favorites, "user_b", page = 1, page_size = 40))
			self.assertEqual(len(result), 10)

			# comments:
			for obj in objs:
				for i in range(20):
					user = "user_a"

					if i % 2 == 0:
						user = "user_b"

					self.__test_method__(a.add_comment, user, guid = obj["guid"], text = util.generate_junk(128))

			for obj in objs:
				comments = self.__cursor_to_array__(self.__test_method__(a.get_comments, user, guid = obj["guid"], page = 0, page_size = 50))
				self.assertEqual(len(comments), 20)

			# create friendship:
			self.__test_method__(a.follow, "user_a", user = "user_b", follow = True)
			self.__test_method__(a.follow, "user_b", user = "user_a", follow = True)

			# recommendations:
			for obj in objs:
				self.__test_method__(a.recommend, "user_a", guid = obj["guid"], receivers = [ "user_b", "user_c" ])

			result = self.__cursor_to_array__(self.__test_method__(a.get_recommendations, "user_b", page = 0, page_size = 100))
			self.assertEqual(len(result), 100)

			result = self.__cursor_to_array__(self.__test_method__(a.get_recommendations, "user_b", page = 1, page_size = 99))
			self.assertEqual(len(result), 1)

			result = self.__cursor_to_array__(self.__test_method__(a.get_recommendations, "user_c", page = 0, page_size = 100))
			self.assertEqual(len(result), 0)

			# messages:
			messages = self.__cursor_to_array__(self.__test_method__(a.get_messages, "user_a", limit = 10, older_than = None))
			self.assertEqual(len(messages), 1)

			messages = self.__cursor_to_array__(self.__test_method__(a.get_messages, "user_b", limit = 200, older_than = None))
			self.assertEqual(len(messages), 101)

	def setUp(self):
		def __create_account__(username, email):
			code = self.__app.request_account(username, email)

			user, email, password = self.__app.activate_user(code)
			self.__users[username] = { "email": email, "password": password }

		self.__clear_tables__()
		util.remove_all_files(config.AVATAR_DIR)

		# create test accounts:
		self.__app = app.AuthenticatedApplication()
		self.__users = {}

		for c in [ "a", "b", "c" ]:
			__create_account__("user_%s" % c, "user_%s@testmail.com" % c)

	def tearDown(self):
		self.__clear_tables__()
		util.remove_all_files(config.AVATAR_DIR)

	def __create_signature__(self, username, password, **kwargs):
			req = app.RequestData(username)
			req.signature = util.sign_message(util.hash(password), username = username, timestamp = req.timestamp, **kwargs)

			return req

	def __test_method__(self, f, username, **kwargs):
		password = self.__users[username]["password"]
		req = self.__create_signature__(username, password, **kwargs)
		
		return f(req, **kwargs)

	def __test_failed_method__(self, f, username, code, **kwargs):
		err = False

		try:
			self.__test_method__(f, username, **kwargs)

		except exception.Exception, ex:
			self.assertEqual(ex.code, code)
			err = True

		self.assertTrue(err)

class TestHttpServer(unittest.TestCase, TestCase):
	def test_00_create_user_accounts(self):
		password = self.__create_user__("user_a", "user_a@testmail.com")
		password = self.__create_user__("user_b", "user_b@testmail.com")

		with factory.create_user_db() as db:
			result = self.__cursor_to_array__(db.search_user("testmail.com"))
			self.assertEqual(len(result), 2)

	def test_01_update_users(self):
		password = self.__create_user__("user_a", "user_a@testmail.com")
		
		# update password:
		new_password = util.generate_junk(16)
		self.client.update_password("user_a", password, new_password)

		# update details:
		self.client.update_user_details("user_a", new_password, "user_a@testmail.org", "firstname", "lastname", "f", "de", False)

		# get details:
		details = json.loads(self.client.get_user_details("user_a", new_password, "user_a"))
		self.assertEqual(details["name"], "user_a")
		self.assertEqual(details["firstname"], "firstname")
		self.assertEqual(details["lastname"], "lastname")
		self.assertEqual(details["email"], "user_a@testmail.org")
		self.assertEqual(details["gender"], "f")
		self.assertEqual(details["language"], "de")
		self.assertIsNone(details["avatar"])
		self.assertFalse(details["protected"])

		# update avatar:
		self.client.update_avatar("user_a", new_password, os.path.join("test-data", "avatar02.jpg"))
		details = json.loads(self.client.get_user_details("user_a", new_password, "user_a"))
		self.assertIsNotNone(details["avatar"])

	def test_02_reset_password(self):
		# create test user:
		self.__create_user__("user_a", "user_a@testmail.com")

		# request new password:
		self.client.request_password("user_a", "user_a@testmail.com")

		# get password reset URL from mail:
		with factory.create_mail_db() as db:
			mail = db.get_unsent_messages()[0]
			db.mark_sent(mail["id"])

			m = re.search("(http://.*)\n", mail["body"])
			url = m.group()

			# reset password:
			self.client.get(url)

			# get new password:
			mail = db.get_unsent_messages()[0]
			db.mark_sent(mail["id"])

			m = re.search("login:\r\n\r\n(.*)\r\n\r\n", mail["body"])
			password = m.group(1)

			with app.Application() as a:
				self.assertTrue(a.validate_password("user_a", password))

	def test_03_disable_account(self):
		# create test user:
		password = self.__create_user__("user_a", "user_a@testmail.com")

		# disable account:
		self.client.disable_user("user_a", password, "user_a@testmail.com")

		# check if account has been disabled successfully:
		with factory.create_user_db() as db:
			self.assertTrue(db.user_is_blocked("user_a"))

	def test_04_search_users(self):
		users = {}
		i = 0

		for c in [ "a", "b", "c", "d", "e", "f" ]:
			name = "user_%s" % c

			if i % 2 == 0:
				email = "%s@testmail.com" % name
			else:
				email = "%s@testmail.org" % name

			users["user_%s" % c] = self.__create_user__(name, email)

			i += 1

		result = json.loads(self.client.find_user("user_a", users["user_a"], "testmail.com"))
		self.assertEqual(len(result), 2)

		result = json.loads(self.client.find_user("user_a", users["user_a"], "testmail.org"))
		self.assertEqual(len(result), 3)

		result = json.loads(self.client.find_user("user_a", users["user_a"], "testmail"))
		self.assertEqual(len(result), 5)

		result = json.loads(self.client.find_user("user_a", users["user_a"], "user_b"))
		self.assertEqual(len(result), 1)

	def test_05_objects(self):
		# create test users & objects:
		password_a = self.__create_user__("user_a", "user_a@testmail.com")
		password_b = self.__create_user__("user_b", "user_b@testmail.com")
		objs = self.__generate_objects__(100)

		# get objects:
		for obj in objs[:10]:
			details = json.loads(self.client.get_object("user_a", password_a, obj["guid"]))
			self.assertEqual(details["guid"], obj["guid"])

		result = json.loads(self.client.get_objects("user_a", password_a, 0, 50))
		self.assertEqual(len(result), 50)

		result = json.loads(self.client.get_objects("user_a", password_a, 1, 90))
		self.assertEqual(len(result), 10)

		result = json.loads(self.client.get_random_objects("user_a", password_a, 50))
		self.assertEqual(len(result), 50)

		for obj in objs[:15]:
			self.client.add_tags("user_a", password_a, obj["guid"], ( "foo", "bar" ))

		result = json.loads(self.client.get_tagged_objects("user_a", password_a, "foo", 0, 50))
		self.assertEqual(len(result), 15)

		result = json.loads(self.client.get_tagged_objects("user_a", password_a, "foobar", 0, 50))
		self.assertEqual(len(result), 0)

		# score:
		for obj in objs[:20]:
			for i in range(2):
				up = True

				if random.randint(0, 100) >= 70:
					up = False

				user = "user_a"
				password = password_a

				if i == 1:
					user = "user_b"
					password = password_b
				
				self.client.rate(user, password, obj["guid"], up = up)

		result = json.loads(self.client.get_popular_objects("user_a", password_a, 0, 15))
		self.assertEqual(len(result), 15)

		for i in range(14):
			assert result[i]["score"]["total"] >= result[i + 1]["score"]["total"]

		# favorites:
		for i in range(20):
			user = "user_a"
			password = password_a

			if i % 2 == 0:
				user = "user_b"
				password = password_b

			self.client.favor(user, password, objs[i]["guid"], favor = True)

		result = json.loads(self.client.get_favorites("user_a", password_a, 0, 15))
		self.assertEqual(len(result), 10)

		result = json.loads(self.client.get_favorites("user_a", password_a, 1, 9))
		self.assertEqual(len(result), 1)

		# comments:
		for obj in objs[:5]:
			for i in range(4):
				user = "user_a"
				password = password_a

				if i % 2 == 0:
					user = "user_b"
					password = password_b

				self.client.add_comment(user, password, obj["guid"], util.generate_junk(128))

		for obj in objs[:5]:
			comments = json.loads(self.client.get_comments("user_a", password_a, obj["guid"], 0, 10))
			self.assertEqual(len(comments), 4)

			comments = json.loads(self.client.get_comments("user_b", password_b, obj["guid"], 1, 3))
			self.assertEqual(len(comments), 1)

		# create frienship:
		self.client.follow("user_a", password_a, "user_b")
		self.client.follow("user_b", password_b, "user_a")

		# recommendations:
		for obj in objs[:10]:
			self.client.recommend("user_a", password_a, obj["guid"], ( "user_a", "user_b" ))

		result = json.loads(self.client.get_recommendations("user_a", password_a, 0, 100))
		self.assertEqual(len(result), 0)

		result = json.loads(self.client.get_recommendations("user_b", password_b, 0, 100))
		self.assertEqual(len(result), 10)

		result = json.loads(self.client.get_recommendations("user_b", password_b, 1, 8))
		self.assertEqual(len(result), 2)

		# messages:
		messages = json.loads(self.client.get_messages("user_a", password_a, 100, None))
		self.assertEqual(len(messages), 1)

		messages = json.loads(self.client.get_messages("user_b", password_b, 100, None))
		self.assertEqual(len(messages), 11)
		timestamp = int(messages[0]["timestamp"]) - 1000

		messages = json.loads(self.client.get_messages("user_b", password_b, 100, timestamp))
		assert len(messages) > 0

	def setUp(self):
		# get test url & port:
		self.port = 80

		m = re.match("(http://.*):(\d+)", config.WEBSITE_URL)

		if m is None:
			self.url = config.WEBSITE_URL
		else:
			self.url = m.group(1)
			self.port = int(m.group(2))

		# create test client:
		self.client = client.Client(self.url, self.port)

		# clear tables & remove test files:
		self.__clear_tables__()
		util.remove_all_files(config.AVATAR_DIR)

	def tearDown(self):
		self.__clear_tables__()
		util.remove_all_files(config.AVATAR_DIR)

	def __create_user__(self, username, email):
		# send account request:
		response = self.client.request_account(username, email)

		with factory.create_mail_db() as db:
			# get activation code from generated mail:
			mail = db.get_unsent_messages()[0]
			db.mark_sent(mail["id"])

			m = re.search("(http://.*)\n", mail["body"])
			url = m.group()

			self.client.get(url)

			mail = db.get_unsent_messages()[0]
			db.mark_sent(mail["id"])

			m = re.search("login:\r\n\r\n(.*)\r\n\r\n", mail["body"])
			password = m.group(1)

			return password

	def __generate_objects__(self, count):
		objs = []

		with factory.create_object_db() as db:
			for i in range(count):
				obj = { "guid": util.generate_junk(32), "source": util.generate_junk(64) }
				db.create_object(obj["guid"], obj["source"])
				objs.append(obj)

		return objs

def run_test_case(case):
	suite = unittest.TestLoader().loadTestsFromTestCase(case)
	unittest.TextTestRunner(verbosity = 2).run(suite)

if __name__ == "__main__":
	for case in [ TestUserDb, TestObjectDb, TestStreamDb, TestMailDb, TestRequestDb, TestApplication, TestAuthenticatedApplication, TestHttpServer ]:
		run_test_case(case)
