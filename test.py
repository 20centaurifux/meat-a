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
"""

import unittest, factory, util, exception, config, string, random, re, itertools, datetime

class TestBase:
	def __init__(self): pass

	def clear(self, scope):
		db = factory.create_test_db()
		db.clear(scope)

	def pick_one(self, arr):
		return arr[random.randint(0, len(arr) - 1)]

	def generate_username(self):
		return self.generate_text(1, 1, string.ascii_letters) + self.generate_text(1, 15)

	def generate_email(self):
		domains = ["com", "net", "de", "org", "biz", "co.uk"]

		return self.generate_text(2, 10) + "@" + self.generate_text(1, 10, string.ascii_letters) + "." +  self.pick_one(domains)

	def generate_text(self, min=20, max=30, characters=string.ascii_letters + string.digits):
		result = []

		for i in range(random.randint(min, max)):
			result.append(self.pick_one(characters))

		return "".join(result)

	def generate_set(self, count, f):
		l = []

		while len(l) < count:
			text = f()

			if len(filter(lambda s: s.lower() == text.lower(), l)) == 0:
				l.append(text)

		return l

	def generate_sex(self):
		sex = ["male", "female", "trans man", "trans woman"]

		return self.pick_one(sex)

	def generate_language(self):
		return self.pick_one(config.LANGUAGES)

	def generate_user_account(self, scope):
		db = factory.create_user_db()

		username = self.generate_username()
		email = self.generate_email()

		while db.username_or_email_assigned(scope, username, email):
			username = self.generate_username()
			email = self.generate_email()

		id = self.generate_text()

		while db.user_request_id_exists(scope, id):
			id = self.generate_text()

		code = self.generate_text()
		password = self.generate_text()
		salt = self.generate_text()
		hash = util.password_hash(password, salt)

		db.create_user_request(scope, id, code, username, email)
		db.activate_user(scope, id, code, hash, salt)

		user = db.get_user(scope, username)
		user.update({ "password": password })

		return user

	def generate_object(self, scope):
		db = factory.create_object_db()

		guid = str(util.new_guid())
		source = self.generate_text()

		db.create_object(scope, guid, source)

		return { "guid": guid, "source": source }

	def assertNoneOrEmpty(self, str):
		assert(str is None or len(str) == 0)

	def assertExceptionRaised(self, f, *args):
		raised = False

		try:
			apply(f, args)

		except:
			raised = True

		assert(raised == True)

	def assertPaging(self, count, eq, f, *args):
		all = apply(f, list(args) + [0, count])
		assert(len(all) == count)

		all = apply(f, list(args) + [0, count * 2])
		assert(len(all) == count)

		empty = apply(f, list(args) + [0, 0])
		assert(len(empty) == 0)

		if count > 1:
			d =  count / 2
			r = count % 2

			pages = []

			for i in range(3):
				pages.append(apply(f, list(args) + [i, d]))

			assert(len(pages[0]) == d)
			assert(len(pages[1]) == d)
			assert(len(pages[2]) == r)

			assert(self.sequencesAreEqual(pages[0], pages[1], eq) == False)
			assert(self.sequencesAreEqual(pages[0], pages[2], eq) == False)
			assert(self.sequencesAreEqual(pages[1], pages[2], eq) == False)

			if count > 1:
				a = apply(f, list(args) + [0, 2])
				b = apply(f, list(args) + [1, 1])

				assert(eq(a[1], b[0]) == True)

	def sequencesAreEqual(self, a, b, eq=lambda a, b: a == b):
			if len(a) != len(b):
				return False

			for e in a:
				if not self.contains(b, eq, e):
					return False

			for e in b:
				if not self.contains(a, eq, e):
					return False

			return True

	def contains(self, l, eq, e):
		for i in l:
			if eq(i, e):
				return True

		return False

class TestUserDb(unittest.TestCase, TestBase):
	def setUp(self):
		self.__connection = factory.create_db_connection()

	def tearDown(self):
		self.__connection.close()

	def test_00_user_request(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# generate test data:
			db = factory.create_user_db()

			requests = []
			size = 10

			usernames = self.generate_set(size * 2, self.generate_username)
			emails = self.generate_set(size * 2, self.generate_email)
			ids = self.generate_set(size * 2, self.generate_text)

			# create account requests:
			for i in range(size):
				requests.append({ "username": usernames[i], "email": emails[i], "id": ids[i], "code": self.generate_text() })

			for r in requests:
				db.create_user_request(scope, r["id"], r["code"], r["username"], r["email"])

			# find & get requests:
			for r in requests:
				self.assertTrue(db.user_request_id_exists(scope, r["id"]))

				req = db.get_user_request(scope, r["id"])

				self.assertEqual(r["id"], req["request_id"])
				self.assertEqual(r["code"], req["request_code"])
				self.assertEqual(r["username"], req["username"])
				self.assertEqual(r["email"], req["email"])

				self.assertTrue(db.username_or_email_assigned(scope, r["username"], r["email"]))

			# check non-existing ids & users:
			for i in range(size, size * 2):
				id = ids[i]
				username = usernames[i]
				email = emails[i]

				self.assertFalse(db.user_request_id_exists(scope, id))
				self.assertIsNone(db.get_user_request(scope, id))
				self.assertFalse(db.username_or_email_assigned(scope, username, email))

			for r in requests:
				self.assertFalse(db.user_exists(scope, r["username"]))

	def test_01_user_activation(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# generate test data:
			db = factory.create_user_db()

			data = []
			size = 10

			usernames = self.generate_set(size * 2, self.generate_username)
			emails = self.generate_set(size * 2, self.generate_email)
			ids = self.generate_set(size * 2, self.generate_text)
			codes = self.generate_set(size * 2, self.generate_text)

			# create account requests:
			for i in range(size):
				data.append({ "username": usernames[i], "email": emails[i], "id": ids[i], "code": codes[i],
				              "password": self.generate_text(), "salt": self.generate_text() })

			for i in range(size):
				r = data[i]
				db.create_user_request(scope, r["id"], r["code"], r["username"], r["email"])

			# activate accounts:
			for i in range(size):
				r = data[i]

				# test wrong code:
				self.assertExceptionRaised(db.activate_user, scope, r["id"], codes[i + 1], r["password"], r["salt"])

				# use correct code:
				db.activate_user(scope, r["id"], r["code"], r["password"], r["salt"])

				self.assertFalse(db.user_request_id_exists(scope, r["id"]))
				self.assertIsNone(db.get_user_request(scope, r["id"]))
				self.assertTrue(db.username_or_email_assigned(scope, r["username"], r["email"]))
				self.assertTrue(db.user_exists(scope, r["username"]))

			# check non-existing ids:
			for i in range(size, size * 2):
				id = ids[i]
				username = usernames[i]
				email = emails[i]
				code = codes[i]

				self.assertExceptionRaised(db.activate_user, scope, id, code, self.generate_text(), self.generate_text())

	def test_02_user_details(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test accounts & update details:
			db = factory.create_user_db()

			for _ in range(100):
				user = self.generate_user_account(scope)

				self.assertTrue(db.user_exists(scope, user["username"]))
				self.assertFalse(db.user_is_blocked(scope, user["username"]))

				db.delete_user(scope, user["username"], True)
				self.assertFalse(db.user_exists(scope, user["username"]))

				db.delete_user(scope, user["username"], False)
				self.assertTrue(db.user_exists(scope, user["username"]))

				db.block_user(scope, user["username"], True)
				self.assertTrue(db.user_is_blocked(scope, user["username"]))

				db.block_user(scope, user["username"], False)
				self.assertFalse(db.user_is_blocked(scope, user["username"]))

				hash, salt = db.get_user_password(scope, user["username"])
				self.assertEqual(util.password_hash(user["password"], salt), hash)

				details = db.get_user(scope, user["username"])

				for k in ["id", "username", "firstname", "lastname", "email", "gender", "created_on", "avatar", "protected", "blocked", "language"]:
					self.assertTrue(details.has_key(k))

					if k in ["username", "email"]:
						self.assertEqual(details[k], user[k])
					elif isinstance(details[k], str):
						self.assertNoneOrEmpty(details[k])

				details["firstname"] = self.generate_text()
				details["lastname"] = self.generate_text()
				details["email"] = self.generate_email()
				details["gender"] = self.generate_sex()
				details["language"] = self.generate_language()
				details["avatar"] = self.generate_text()

				params = [scope] + util.select_values(details, ["username", "email", "firstname", "lastname", "gender", "language", "protected"])
				apply(db.update_user_details, params)

				db.update_avatar(scope, user["username"], details["avatar"])

				new_details = db.get_user(scope, user["username"])

				for k in new_details.keys():
					self.assertEqual(details[k], new_details[k])

				user["password"] = self.generate_text()

				salt = self.generate_text()
				hash = util.password_hash(user["password"], salt)

				db.update_user_password(scope, user["username"], hash, salt)

				hash, salt = db.get_user_password(scope, user["username"])
				self.assertEqual(util.password_hash(user["password"], salt), hash)

	def test_03_password_reset(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			db = factory.create_user_db()

			for _ in range(100):
				# create user account:
				user = self.generate_user_account(scope)

				# request password change:
				id = self.generate_text()
				code = self.generate_text()

				self.assertFalse(db.password_request_id_exists(scope, id))

				db.create_password_request(scope, id, code, user["id"])

				self.assertTrue(db.password_request_id_exists(scope, id))

				# set new password:
				new_password = self.generate_text()
				new_salt = self.generate_text()
				new_hash = util.password_hash(new_password, new_salt)

				self.assertExceptionRaised(db.reset_password, scope, id, self.generate_text(), new_hash, new_salt)

				db.reset_password(scope, id, code, new_hash, new_salt)
				self.assertFalse(db.password_request_id_exists(scope, id))

				hash, salt = db.get_user_password(scope, user["username"])
				self.assertEqual(hash, new_hash)
				self.assertEqual(salt, new_salt)

				# create and remove password requests:
				id = self.generate_text()
				code = self.generate_text()

				db.create_password_request(scope, id, code, user["id"])

				self.assertTrue(db.password_request_id_exists(scope, id))

				db.remove_password_requests_by_user_id(scope, user["id"])

				self.assertFalse(db.password_request_id_exists(scope, id))

	def test_04_map_id(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# map user ids:
			db = factory.create_user_db()

			for _ in range(10):
				user = self.generate_user_account(scope)
				self.assertEqual(user["username"], db.map_user_id(scope, user["id"]))

	def test_05_change_email(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			db = factory.create_user_db()

			for _ in range(100):
				# create test accoutns:
				a = self.generate_user_account(scope)
				b = self.generate_user_account(scope)

				# test if emails can be changed:
				self.assertTrue(db.user_can_change_email(scope, a["username"], a["email"]))
				self.assertFalse(db.user_can_change_email(scope, a["username"], b["email"]))
				self.assertFalse(db.user_can_change_email(scope, b["username"], a["email"]))

				# set new email address:
				new_email = self.generate_email()

				while not db.user_can_change_email(scope, a["username"], new_email):
					new_email = self.generate_email()

				details = db.get_user(scope, a["username"])

				details["email"] = new_email

				params = [scope] + util.select_values(details, ["username", "email", "firstname", "lastname", "gender", "language", "protected"])
				apply(db.update_user_details, params)

				details = db.get_user(scope, a["username"])
				self.assertEqual(details["email"], new_email)

	def test_06_search(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# generate test accounts:
			db = factory.create_user_db()

			users = []

			for i in range(1000):
				user = self.generate_user_account(scope)

				if i % 7 == 0:
					db.delete_user(scope, user["username"], True)
				else:
					user["firstname"] = self.generate_text()
					user["lastname"] = self.generate_text()

					db.update_user_details(scope, user["username"], user["email"], user["firstname"], user["lastname"], "male", "en", True)

					for k in user.keys():
						if isinstance(user[k], str):
							user[k] = user[k].lower()

					users.append(user)

			# search for test accounts:
			for _ in range(10):
				user = users[random.randint(0, len(users) - 1)]
				query = user["firstname"].lower()[0:2]
				expected = 0

				for user in users:
					if query in user["username"] or query in user["email"] or query in user["firstname"] or query in user["lastname"]:
						expected += 1

				result = db.search(scope, query)

				self.assertEqual(expected, len(result))

	def test_07_friendship(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			db = factory.create_user_db()

			for _ in range(10):
				# generate test accounts:
				a = self.generate_user_account(scope)
				b = self.generate_user_account(scope)
				c = self.generate_user_account(scope)

				for p in itertools.permutations([a, b, c], 2):
					self.assertFalse(db.is_following(scope, p[0]["username"], p[1]["username"]))

				for u in [a, b, c]:
					followed = db.get_followed_usernames(scope, a["username"])
					self.assertEqual(len(followed), 0)

				# set and test friendship:
				m = { a["id"]: [b, c], b["id"]: [a], c["id"]: [a, b] }

				for k, v in m.items():
					for u in v:
						db.follow(scope, k, u["id"], True)

				for p in itertools.permutations([a, b, c], 2):
					self.assertEqual(db.is_following(scope, p[0]["username"], p[1]["username"]), p[1] in m[p[0]["id"]])

				for u in [a, b, c]:
					for f in m[u["id"]]:
						followed = db.get_followed_usernames(scope, u["username"])

						self.assertEqual(len(followed), len(m[u["id"]]))
						self.assertEqual(len(filter(lambda username: username == f["username"], followed)), 1)

				db.follow(scope, a["id"], c["id"], False)
				db.follow(scope, c["id"], b["id"], False)

				self.assertTrue(db.is_following(scope, a["username"], b["username"]))
				self.assertFalse(db.is_following(scope, a["username"], c["username"]))
				self.assertTrue(db.is_following(scope, c["username"], a["username"]))
				self.assertFalse(db.is_following(scope, c["username"], b["username"]))

			# test invalid usernames:
			self.assertExceptionRaised(db.follow, scope, self.generate_text(), self.generate_text(), True)
			self.assertExceptionRaised(db.follow, scope, self.generate_text(), self.generate_text(), False)

	def test_08_favorites(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test objects:
			db = factory.create_user_db()
			object_db = factory.create_object_db()

			objects = []

			for _ in range(500):
				objects.append(self.generate_object(scope))

			for _ in range(10):
				# create test accounts:
				a = self.generate_user_account(scope)
				b = self.generate_user_account(scope)

				# add and remove favorites:
				for i in range(len(objects)):
					obj = objects[i]

					if i % 5 == 0:
						db.favor(scope, a["id"], obj["guid"], True)

					if i % 10 == 0:
						db.favor(scope, a["id"], obj["guid"], False)

					if i % 7 == 0:
						db.favor(scope, b["id"], obj["guid"], True)

					if i % 14 == 0:
						db.favor(scope, b["id"], obj["guid"], False)

				# test favorites:
				count_a = 0
				count_b = 0

				favs_a = db.get_favorites(scope, a["id"])
				favs_b = db.get_favorites(scope, b["id"])

				for i in range(len(objects)):
					obj = objects[i]

					if i % 5 == 0 and not i % 10 == 0:
						count_a += 1
						self.assertTrue(db.is_favorite(scope, a["id"], obj["guid"]))
					else:
						self.assertFalse(db.is_favorite(scope, a["id"], obj["guid"]))

					if i % 7 == 0 and not i % 14 == 0:
						count_b += 1
						self.assertTrue(db.is_favorite(scope, b["id"], obj["guid"]))
					else:
						self.assertFalse(db.is_favorite(scope, b["id"], obj["guid"]))

				self.assertEqual(count_a, len(favs_a))
				self.assertEqual(count_b, len(favs_b))

				# delete object and test favorites:
				object_db.delete_object(scope, favs_a[0]["guid"], True)

				new_favs = db.get_favorites(scope, a["id"])

				self.assertEqual(len(favs_a) - 1, len(new_favs))
				self.assertEqual(len(filter(lambda f: f["guid"] == favs_a[0]["guid"], new_favs)), 0)

				object_db.delete_object(scope, favs_a[0]["guid"], False)

			# invalid user id and guid:
			self.assertExceptionRaised(db.favor, scope, random.randint(0, pow(2, 32) - 1), str(util.new_guid()))

	def test_09_recommendations(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test objects:
			db = factory.create_user_db()
			object_db = factory.create_object_db()

			objects = []

			for _ in range(100):
				objects.append(self.generate_object(scope))

			for _ in range(10):
				# create test acconts and recommendations:
				a = self.generate_user_account(scope)
				b = self.generate_user_account(scope)

				count_a = 0
				count_b = 0

				for i in range(len(objects)):
					obj = objects[i]

					if i % 5 == 0:
						db.recommend(scope, a["id"], b["id"], obj["guid"])
						count_b += 1

					if i % 10 == 0:
						db.recommend(scope, b["id"], a["id"], obj["guid"])
						count_a += 1

				# test recommendations:
				for i in range(len(objects)):
					obj = objects[i]

					self.assertEqual(db.recommendation_exists(scope, a["username"], b["username"], obj["guid"]), i % 5 == 0)
					self.assertEqual(db.recommendation_exists(scope, b["username"], a["username"], obj["guid"]), i % 10 == 0)

				# paging:
				eq = lambda x, y: x["username"] == y["username"] and x["guid"] == y["guid"]

				self.assertPaging(count_b, eq, db.get_recommendations, scope, b["username"])
				self.assertPaging(count_a, eq, db.get_recommendations, scope, a["username"])

				# delete object and test recommendations:
				recommendations = db.get_recommendations(scope, b["username"], 0, count_b)

				object_db.delete_object(scope, recommendations[0]["guid"], True)

				self.assertEqual(len(recommendations) - 1, len(db.get_recommendations(scope, b["username"], 0, count_b)))

				object_db.delete_object(scope, recommendations[0]["guid"], False)

			# invalid username and guid:
			self.assertExceptionRaised(db.favor, scope, self.generate_username(), self.generate_username(), str(util.new_guid()))

class TestObjectDb(unittest.TestCase, TestBase):
	def setUp(self):
		self.__connection = factory.create_db_connection()

	def tearDown(self):
		self.__connection.close()

	def test_00_general(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create objects:
			db = factory.create_object_db()

			objects = []

			for _ in range(100):
				obj = { "guid": util.new_guid(), "source": self.generate_text() }
				objects.append(obj)

				db.create_object(scope, obj["guid"], obj["source"])

			# test if object exists:
			for obj in objects:
				self.assertTrue(db.object_exists(scope, obj["guid"]))

			for _ in range(100):
				self.assertFalse(db.object_exists(scope, util.new_guid()))

			# delete objects:
			for i in range(0, len(objects), 3):
				db.delete_object(scope, objects[i]["guid"], True)

			for i in range(len(objects)):
				self.assertEqual(db.object_exists(scope, objects[i]["guid"]), i % 3 != 0)

			for i in range(len(objects)):
				db.delete_object(scope, objects[i]["guid"], i % 3 != 0)

			for i in range(len(objects)):
				self.assertEqual(db.object_exists(scope, objects[i]["guid"]), i % 3 == 0)

			# lock objects:
			for i in range(0, len(objects), 7):
				db.lock_object(scope, objects[i]["guid"])

			for i in range(0, len(objects)):
				self.assertEqual(db.is_locked(scope, objects[i]["guid"]), i % 7 == 0)

	def test_01_get_objects(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create objects:
			db = factory.create_object_db()

			objects = []

			for _ in range(100):
				obj = { "guid": util.new_guid(), "source": self.generate_text() }
				objects.append(obj)

				db.create_object(scope, obj["guid"], obj["source"])

			# test details:
			for obj in objects:
				data = db.get_object(scope, obj["guid"])

				self.assertEqual(obj["guid"], data["guid"])
				self.assertEqual(obj["source"], data["source"])

				self.assertFalse(data["locked"])
				self.assertFalse(data["reported"])
				self.assertEqual(len(data["tags"]), 0)
				self.assertEqual(data["comments_n"], 0)
				self.assertIsInstance(data["created_on"], datetime.datetime)
				self.assertEqual(data["score"]["up"], 0)
				self.assertEqual(data["score"]["down"], 0)
				self.assertEqual(data["score"]["fav"], 0)

			# lock objects and test lock field:
			for i in range(0, len(objects), 3):
				db.lock_object(scope, objects[i]["guid"])

			for i in range(len(objects)):
				obj = db.get_object(scope, objects[i]["guid"])
				self.assertEqual(obj["locked"], i % 3 == 0)

			# paging:
			eq = lambda a, b: a["guid"] == b["guid"] and a["source"] == b["source"]
			self.assertPaging(len(objects), eq, db.get_objects, scope)

	def test_02_vote(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test data:
			db = factory.create_object_db()
			user_db = factory.create_user_db()

			objects = []
			size = 50

			for _ in range(size):
				obj = self.generate_object(scope)

				sep = []

				sep.append(random.randint(9, size * 2 - 20))
				sep.append(random.randint(sep[0] + 1, size * 2 - 10))
				sep.append(random.randint(9, size * 2 - 20))

				obj["separators"] = sep

				score = {}

				score["up"] = sep[0]
				score["down"] = sep[1] - sep[0]
				score["fav"] = sep[2]

				obj["score"] = score

				objects.append(obj)

			users = []

			for _ in range(size * 2):
				users.append(self.generate_user_account(scope))

			# let users vote:
			for obj in objects:
				for i in range(obj["separators"][0]):
					db.vote(scope, obj["guid"], users[i]["id"], True)

				for i in range(obj["separators"][0], obj["separators"][1]):
					db.vote(scope, obj["guid"], users[i]["id"], False)

				for i in range(obj["separators"][2]):
					user_db.favor(scope, users[i]["id"], obj["guid"])

			# test score:
			for obj in objects:
				for i in range(size * 2):
					self.assertEqual(db.user_can_vote(scope, obj["guid"], users[i]["username"]), i >= obj["separators"][1])

					voting = db.get_voting(scope, obj["guid"], users[i]["username"])

					if i < obj["separators"][1]:
						self.assertEqual(voting, i < obj["separators"][0])
					else:
						self.assertIsNone(voting)

				details = db.get_object(scope, obj["guid"])

				self.assertEqual(obj["score"]["up"], details["score"]["up"])
				self.assertEqual(obj["score"]["down"], details["score"]["down"])
				self.assertEqual(obj["score"]["fav"], details["score"]["fav"])

			# paging:
			eq = lambda a, b: a["guid"] == b["guid"] and a["source"] == b["source"]
			self.assertPaging(len(objects), eq, db.get_popular_objects, scope)

			# test sort order:
			prev_score = size * 4

			for obj in db.get_popular_objects(scope, 0, size):
				score = obj["score"]["up"] - obj["score"]["down"] + obj["score"]["fav"]

				self.assertTrue(score <= prev_score)

				prev_score = score

	def test_03_tags(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test data:
			db = factory.create_object_db()
			user_db = factory.create_user_db()

			objects = []
			users = []

			# generate users and tags:
			tags = self.generate_set(20, lambda: self.generate_text(2, 16).lower())

			for _ in range(len(tags)):
				users.append(self.generate_user_account(scope))

			for _ in range(50):
				obj = self.generate_object(scope)

				indeces = range(len(tags))
				random.shuffle(indeces)
				indeces = indeces[:random.randint(1, len(indeces) - 1)]

				obj["indeces"] = indeces
				obj["count"] = map(lambda _: random.randint(1, len(users)), range(len(indeces)))

				objects.append(obj)

			# generate objects and add tags:
			for obj in objects:
				for i in range(len(obj["indeces"])):
					count = obj["count"][i]
					tag = tags[obj["indeces"][i]]

					for m in range(count):
						db.add_tag(scope, obj["guid"], users[m]["id"], tag)
						self.assertExceptionRaised(db.add_tag, scope, obj["guid"], users[m]["id"], tag)

			# test tag cloud:
			prev_count = len(tags) * len(objects)

			for m in db.get_tags(scope):
				tag = m["tag"]
				count = m["count"]

				self.assertTrue(count <= prev_count)
				prev_count = count

				index = tags.index(tag)
				sum = 0

				for obj in objects:
					if index in obj["indeces"]:
						pos = obj["indeces"].index(index)
						sum += obj["count"][pos]

				self.assertEqual(sum, count)

			# get tags of each object:
			for obj in objects:
				details = db.get_object(scope, obj["guid"])
				equal = self.sequencesAreEqual(obj["indeces"], map(lambda t: tags.index(t), details["tags"]))

				self.assertTrue(equal)

			# paging:
			for t in tags:
				sum = 0

				for obj in objects:
					if tags.index(t) in obj["indeces"]:
						sum += 1

				self.assertPaging(sum, lambda a, b: a["guid"] == b["guid"], db.get_tagged_objects, scope, t)

	def test_04_comments(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test data:
			db = factory.create_object_db()
			user_db = factory.create_user_db()

			objects = []
			users = []
			comments = {}

			for _ in range(50):
				users.append(self.generate_user_account(scope))

			for _ in range(100):
				objects.append(self.generate_object(scope))

			for obj in objects:
				l = []

				size = random.randint(0, 100)
				text = self.generate_set(size, self.generate_text)

				for t in text:
					user = self.pick_one(users)

					comment = { "guid": obj["guid"], "username": user["username"], "text": t }
					l.append(comment)

					db.add_comment(scope, obj["guid"], user["id"], t)

				comments[obj["guid"]] = l

			# get comments:
			eq = lambda a, b: a["text"] == b["text"]

			for k, v in comments.items():
				# paging:
				self.assertPaging(len(v), eq, db.get_comments, scope, k)

				# get all comments:
				l = db.get_comments(scope, k, 0, len(v))

				self.assertTrue(self.sequencesAreEqual(l, v, lambda a, b: a["text"] == b["text"] and a["username"] == b["username"]))

				# get single comment:
				for c in l:
					details = db.get_comment(scope, c["id"])

					self.assertEqual(details["id"], c["id"])
					self.assertEqual(details["text"], c["text"])
					self.assertEqual(details["username"], c["username"])

			# delete comments:
			for guid in comments.keys():
				deleted = []

				first = db.get_comments(scope, guid, 0, 100)

				for i in range(0, len(first), 3):
					db.flag_comment_deleted(scope, first[i]["id"])
					deleted.append(first[i]["id"])

				second = db.get_comments(scope, guid, 0, 100)

				self.assertTrue(self.sequencesAreEqual(first, second, lambda a, b: a["id"] == b["id"] and a["text"] == b["text"]))

				count = 0

				for c in second:
					if c["deleted"]:
						count += 1

						self.assertTrue(c["id"] in deleted)

				self.assertEqual(count, len(deleted))

	def test_05_abuse(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			db = factory.create_object_db()

			objects = []

			for _ in range(1000):
				obj = { "guid": util.new_guid(), "source": self.generate_text() }
				objects.append(obj)

				db.create_object(scope, obj["guid"], obj["source"])

			for i in range(0, len(objects), 3):
				db.report_abuse(scope, objects[i]["guid"])

			for i in range(0, len(objects), 3):
				details = db.get_object(scope, objects[i]["guid"])

				self.assertEqual(details["reported"], i % 3 == 0)

	def test_06_random(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			db = factory.create_object_db()

			objects = {}

			for _ in range(100):
				guid = util.new_guid()

				objects[guid] = 0

				obj = { "guid": guid, "source": self.generate_text() }
				db.create_object(scope, obj["guid"], obj["source"])

			empty = db.get_random_objects(scope, 0)
			self.assertEqual(len(empty), 0)

			half = db.get_random_objects(scope, 50)
			self.assertEqual(len(half), 50)

			all = db.get_random_objects(scope, 100)
			self.assertEqual(len(all), 100)

			for obj in all:
				objects[obj["guid"]] = 1

			for guid in objects:
				self.assertEqual(objects[guid], 1)

			for _ in range(10000):
				for obj in db.get_random_objects(scope, 10):
					objects[obj["guid"]] = objects[obj["guid"]] + 1

			for v in objects.values():
				self.assertTrue(v >= 800 and v <= 1200)

class TestStreamDb(unittest.TestCase, TestBase):
	def setUp(self):
		self.__connection = factory.create_db_connection()

	def tearDown(self):
		self.__connection.close()

	def test_00_friendship(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			db = factory.create_stream_db()
			user_db = factory.create_user_db()

			a, b, c = map(lambda _: self.generate_user_account(scope), range(3))

			user_db.follow(scope, a["id"], b["id"], True)
			user_db.follow(scope, b["id"], a["id"], True)
			user_db.follow(scope, a["id"], c["id"], True)
			user_db.follow(scope, a["id"], c["id"], False)

			for user in [a, b]:
				messages = db.get_messages(scope, user["username"])

				self.assertEqual(len(messages), 1)
				msg = messages[0]

				if user is a:
					friend = long(b["id"])
				else:
					friend = long(a["id"])

				source = long(msg["source"])

				self.assertTrue(msg["type"] == "following")
				self.assertEqual(source, friend)

			messages = db.get_messages(scope, c["username"])
			self.assertEqual(len(messages), 2)

			for msg in messages:
				source = long(msg["source"])

				self.assertTrue(msg["type"] == "following" or msg["type"] == "unfollowing")
				self.assertEqual(source, a["id"])

	def test_01_recommendations(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test data:
			db = factory.create_stream_db()
			user_db = factory.create_user_db()

			users = map(lambda _: self.generate_user_account(scope), range(10))
			objects = map(lambda _: self.generate_object(scope), range(1000))

			m = {}

			for receiver in users:
				d = {}

				senders = [user["id"] for user in filter(lambda u: u["id"] != receiver["id"], users)]
				random.shuffle(senders)

				for sender in senders[:random.randint(1, len(senders) - 2)]:
					d[sender] = random.randint(2, 20)

				m[receiver["id"]] = d

			for i in range(len(objects)):
				for receiver_id, senders in m.items():
					for sender_id, n in senders.items():
						if i % n == 0:
							user_db.recommend(scope, sender_id, receiver_id, objects[i]["guid"])

			# get and test messages:
			for user in users:
				messages = db.get_messages(scope, user["username"])

				for msg in messages:
					self.assertEqual(msg["type"], "recommendation")

					source = int(msg["source"])

					index = filter(lambda i: objects[i]["guid"] == msg["target"], range(len(objects)))[0]

					self.assertTrue(index % m[user["id"]][source] == 0)


	def test_02_comment_and_vote(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

			# create test data:
			db = factory.create_stream_db()
			user_db = factory.create_user_db()
			object_db = factory.create_object_db()

			a, b, c = map(lambda _: self.generate_user_account(scope), range(3))
			objects = map(lambda _: self.generate_object(scope), range(1000))

			user_db.follow(scope, a["id"], b["id"], True)
			user_db.follow(scope, b["id"], a["id"], True)

			user_db.update_user_details(scope, c["username"], c["email"], None, None, None, None, False)

			comment_stat = {}
			vote_stat = {}

			for user in [a, b, c]:
				comment_stat[user["id"]] = {}
				vote_stat[user["id"]] = {}

			for obj in objects:
				guid = obj["guid"]
				author = long(self.pick_one([a["id"], b["id"], c["id"]]))

				# add comments:
				for _ in range(random.randint(1, 50)):
					object_db.add_comment(scope, guid, author, self.generate_text())

					if comment_stat[author].has_key(guid):
						comment_stat[author][guid] = comment_stat[author][guid] + 1
					else:
						comment_stat[author][guid] = 1

				# vote:
				object_db.vote(scope, guid, author, random.randint(0, 1) == 1)

				if vote_stat[author].has_key(guid):
					vote_stat[author][guid] = vote_stat[author][guid] + 1
				else:
					vote_stat[author][guid] = 1

			# run test:
			for user in [a, b]:
				for msg in db.get_messages(scope, user["username"], pow(2, 31)):
					if user is a:
						friend = long(b["id"])
					else:
						friend = long(a["id"])

					source = long(msg["source"])
					target = msg["target"]

					self.assertTrue(msg["type"] in ["following", "wrote-comment", "voted-object"])
					self.assertEqual(source, friend)

					if msg["type"] == "wrote-comment":
						comment = object_db.get_comment(scope, target)

						guid = comment["object-guid"]
						comment_stat[source][guid] = comment_stat[source][guid] - 1
					elif msg["type"] == "voted-object":
						vote_stat[source][target] = vote_stat[source][target] - 1

			messages = db.get_messages(scope, c["username"], 100)
			self.assertEqual(len(messages), 0)

			for msg in db.get_public_messages(scope, pow(2, 31)):
				source = long(msg["source"])

				self.assertTrue(msg["type"] in ["wrote-comment", "voted-object"])
				self.assertEqual(source, c["id"])

				if msg["type"] == "wrote-comment":
					target = msg["target"]
					comment = object_db.get_comment(scope, target)

					guid = comment["object-guid"]
					comment_stat[source][guid] = comment_stat[source][guid] - 1
				else:
					vote_stat[source][guid] = vote_stat[source][guid] - 1

			for user in [a, b, c]:
				for v in comment_stat[user["id"]].values():
					self.assertEqual(v, 0)

				for v in vote_stat[user["id"]].values():
					self.assertEqual(v, 0)

class TestMailDb(unittest.TestCase, TestBase):
	def setUp(self):
		self.__connection = factory.create_db_connection()

	def tearDown(self):
		self.__connection.close()

	def test_00_mail(self):
		with self.__connection.enter_scope() as scope:
			self.clear(scope)

		# create test data:
		db = factory.create_mail_db()
		user_db = factory.create_user_db()

		a, b = map(lambda _: self.generate_user_account(scope), range(2))

		bodies = self.generate_set(100, self.generate_text)
		subjects = self.generate_set(100, self.generate_text)

		for i in range(100):
			if i % 4 == 0:
				db.push_user_mail(scope, subjects[i], bodies[i], a["id"])
			elif i % 6 == 0:
				db.push_mail(scope, subjects[i], bodies[i], b["email"])
			elif i % 2 == 0:
				db.push_mail(scope, subjects[i], bodies[i], a["email"])
			else:
				db.push_user_mail(scope, subjects[i], bodies[i], b["id"])

		# get mails:
		empty = db.get_unsent_messages(scope, 0)
		self.assertEqual(len(empty), 0)

		some = db.get_unsent_messages(scope, 10)
		self.assertEqual(len(some), 10)

		all = db.get_unsent_messages(scope, len(bodies) * 2)
		self.assertEqual(len(all), 100)

		for msg in all:
			self.assertTrue(msg["body"] in bodies)
			self.assertTrue(msg["subject"] in subjects)
			self.assertTrue(msg["email"] in [a["email"], b["email"]])

		# set mails sent:
		sent = []

		for i in range(0, 100, 2):
			id = all[i]["id"]

			sent.append(id)
			db.mark_sent(scope, id)

		all = db.get_unsent_messages(scope, len(bodies))
		self.assertEqual(len(all), len(bodies) - len(bodies) / 2)

		for msg in all:
			self.assertFalse(msg["id"] in sent)

def run_test_case(case):
	suite = unittest.TestLoader().loadTestsFromTestCase(case)
	unittest.TextTestRunner(verbosity = 2).run(suite)

if __name__ == "__main__":
	for case in [TestUserDb, TestObjectDb, TestStreamDb, TestMailDb]:
		run_test_case(case)
