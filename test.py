import unittest, factory, util, random, exception
from time import sleep

class TestCase:
	def __cursor_to_array__(self, cur):
		a = []

		for i in cur:
			a.append(i)

		return a

class TestUserDb(unittest.TestCase, TestCase):
	def setUp(self):
		# connect to database:
		self.db = self.__connect_and_prepare__()

		# generate user details:
		self.user_count = 100
		self.default_text_length = 64
		self.users = self.__generate_users__(self.user_count, self.default_text_length)

		# save users in database:
		for user in self.users:
			self.db.create_user(user["name"], user["email"], user["password"], user["firstname"], user["lastname"], user["gender"])

	def tearDown(self):
		self.__clear_tables__(self.db)

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
			self.assertIsNot(details, None)
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
			queries.append("%s, %s" % (user["lastname"], user["firstname"]))

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

	def __connect_and_prepare__(self):
		db = factory.create_user_db()
		self.__clear_tables__(db)

		return db

	def __clear_tables__(self, db):
		db.remove("users")
		db.remove("user_requests")

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

db = factory.create_object_db()

class TestObjectDb(unittest.TestCase, TestCase):
	def setUp(self):
		# connect to database:
		self.db = self.__connect_and_prepare__()

	def tearDown(self):
		self.__clear_tables__(self.db)

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
			sleep(1)

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
			sleep(1)

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
		for i in range(5):
			self.db.favor_object(objs[i]["guid"], "h", True)
			sleep(1)

		r = self.__cursor_to_array__(self.db.get_favorites("h", 0, 5))

		for i in range(5):
			self.assertEqual(objs[4 - i]["guid"], r[i]["guid"])

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
		for i in range(5):
			self.db.recommend(objs[i]["guid"], "a", [ "d" ])
			sleep(1)

		r = self.__cursor_to_array__(self.db.get_recommendations("d", 0, 10))

		for i in range(5):
			self.assertEqual(objs[4 - i]["guid"], r[i]["guid"])

	def test_11_comments(self):
		# create test users:
		userdb = factory.create_user_db()
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
			#sleep(0.5)

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
		self.__clear_tables__(db)

		return db

	def __clear_tables__(self, db):
		db.remove("objects")

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

def run_test_case(case):
	suite = unittest.TestLoader().loadTestsFromTestCase(case)
	unittest.TextTestRunner(verbosity = 2).run(suite)

if __name__ == "__main__":
	for case in [ TestUserDb, TestObjectDb ]:
		run_test_case(case)
