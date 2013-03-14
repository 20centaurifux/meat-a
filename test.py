import unittest, factory, util, random

class TestUserDb(unittest.TestCase):
	def setUp(self):
		# connect to database:
		self.db = self.__connect_and_prepare__()

		# generate user details:
		self.user_count = 100
		self.default_text_length = 64
		self.users = self.__generate_users__(self.user_count, self.default_text_length)

		# save users in database:
		for user in self.users:
			self.db.create_user(user["name"], user["email"], user["firstname"], user["lastname"], user["password"], user["gender"])

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
				result = []

				for entry in self.db.search_user(query):
					result.append(entry)

				# test if search result contains at least one user:
				self.assertTrue(len(result) >= 1)

				# test if current user exists in search result:
				user_exists = False

				for entry in result:
					if entry["name"] == user["name"]:
						user_exists = True
						break

				self.assertTrue(user_exists)

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

db = factory.create_object_db()

class TestObjectDb(unittest.TestCase):
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

			for key in obj:
				self.assertEqual(obj[key], details[key])

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

	def __connect_and_prepare__(self):
		db = factory.create_object_db()
		self.__clear_tables__(db)

		return db

	def __clear_tables__(self, db):
		db.remove("objects")
		db.remove("user_ratings")
		db.remove("user_favorites")

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

if __name__ == "__main__":
	#unittest.main()
	#suite = unittest.TestLoader().loadTestsFromTestCase(TestUserDb)
	suite = unittest.TestLoader().loadTestsFromTestCase(TestObjectDb)
	unittest.TextTestRunner(verbosity=2).run(suite)
