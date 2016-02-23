import database, psycopg2, psycopg2.extras, util, exception, config

class PGTransactionScope(database.TransactionScope):
	def __init__(self, db):
		database.TransactionScope.__init__(self, db)
		self.__db = db
		self.__cursor = None

	def __enter_scope__(self):
		self.__cursor = self.__db.cursor()

	def __leave_scope__(self, commit):
		if commit:
			self.__db.commit()
		else:
			self.__db.rollback()

	def get_handle(self):
		return self.__cursor

def execute_scalar(cur, query, *params):
	cur.execute(query, params)
	row = cur.fetchone()

	if row is not None:
		row = row[0]

	return row

def fetch_one(cur, query, *params):
	cur.execute(query, params)
	row = cur.fetchone()

	return row

def fetch_all(cur, query, *params):
	result = []

	cur.execute(query, params)

	for row in cur.fetchall():
		result.append(row)

	return result

def to_dict(row):
	m = {}

	if not row is None:
		for k in row.keys():
			m[k] = row[k]

	return m

class PGConnection(database.Connection):
	def __init__(self, db, **kwargs):
		database.Connection.__init__(self)

		self.__conn = None
		self.__host = kwargs["host"]
		self.__port = kwargs["port"]
		self.__user = kwargs["username"]
		self.__pwd = kwargs["password"]
		self.__db = db

	def __connect__(self):
		if self.__conn == None:
			cn_str = "host='%s' dbname='%s' port=%d user='%s' password='%s'" % (self.__host, self.__db, self.__port, self.__user, self.__pwd)
			self.__conn = psycopg2.connect(cn_str)

	def __create_transaction_scope__(self):
		self.__connect__()
		return PGTransactionScope(self)

	def cursor(self, factory=psycopg2.extras.DictCursor):
		return self.__conn.cursor(cursor_factory=factory)

	def commit(self):
		self.__conn.commit()

	def rollback(self):
		self.__conn.rollback()

	def close(self):
		if self.__conn is not None:
			self.__conn.close()

class PGDb:
	def __init__(self): pass

	def __build_object__(self, row):
		obj = {}

		for k in ["guid", "source", "locked", "reported", "created_on"]:
			obj[k] = row[k]

		obj["score"] = { "up": row["up"], "down": row["down"], "fav": row["favorites"] }
		obj["comments_n"] = row["comments"]

		return obj

	def __get_tags__(self, cur, guid):
		cur.execute("select distinct(tag) from object_tag where object_guid=%s", (guid,))

		tags = []

		for row in cur.fetchall():
			tags.append(row[0])

		return tags

	def __get_objects__(self, cur, query, *params):
		objs = []

		for row in fetch_all(cur, query, *params):
			objs.append(self.__build_object__(row))

		for obj in objs:
			obj["tags"] = self.__get_tags__(cur, obj["guid"])

		return objs

class TestDb(PGDb, database.TestDb):
	def __init__(self):
		database.TestDb.__init__(self)
		PGDb.__init__(self)

	def clear(self, scope):
		cur = scope.get_handle()

		cur.execute("delete from public_message")
		cur.execute("delete from user_favorite")
		cur.execute("delete from user_recommendation")
		cur.execute("delete from object_score")
		cur.execute("delete from object_tag")
		cur.execute("delete from object_comment")
		cur.execute("delete from object")
		cur.execute("delete from password_request")
		cur.execute("delete from user_friendship")
		cur.execute("delete from user_request")
		cur.execute("delete from mail")
		cur.execute("delete from message")
		cur.execute("delete from \"user\"")

class PGUserDb(PGDb, database.UserDb):
	def __init__(self):
		database.UserDb.__init__(self)
		PGDb.__init__(self)

	def user_request_id_exists(self, scope, id):
		cur = scope.get_handle()

		return execute_scalar(cur, "select count(request_id) from v_user_requests where request_id=%s and datediff<=%s", id, config.USER_REQUEST_TIMEOUT) > 0

	def get_user_request(self, scope, id):
		cur = scope.get_handle()

		req = fetch_one(cur, "select request_id, request_code, username, email, created_on from v_user_requests where datediff<=%s and request_id=%s", config.USER_REQUEST_TIMEOUT, id)

		if req is not None:
			req = to_dict(req)

		return req

	def username_or_email_assigned(self, scope, username, email):
		cur = scope.get_handle()

		return execute_scalar(cur, "select user_name_or_email_assigned(%s, %s, %s)", username, email, config.USER_REQUEST_TIMEOUT)

	def create_user_request(self, scope, id, code, username, email):
		cur = scope.get_handle()
		cur.execute("insert into user_request (request_id, request_code, username, email) values (%s, %s, %s, %s)", (id, code, username, email))

	def activate_user(self, scope, id, code, password, salt):
		cur = scope.get_handle()
		id = execute_scalar(cur, "select * from user_activate(%s, %s, %s, %s, %s)", id, code, password, salt, config.USER_REQUEST_TIMEOUT)

		if id is None:
			raise exception.InternalFailureException("User activation failed.")

		return id

	def user_exists(self, scope, username):
		cur = scope.get_handle()

		return execute_scalar(cur, "select count(id) from \"user\" where iusername=lower(%s) and deleted=false", username) > 0

	def map_user_id(self, scope, user_id):
		cur = scope.get_handle()

		return execute_scalar(cur, "select username from \"user\" where id=%s", user_id)

	def user_is_blocked(self, scope, username):
		cur = scope.get_handle()

		return execute_scalar(cur, "select blocked from \"user\" where iusername=lower(%s)", username)

	def block_user(self, scope, username, blocked=True):
		cur = scope.get_handle()
		cur.execute("update \"user\" set blocked=%s where iusername=lower(%s)", (blocked, username,))

	def delete_user(self, scope, username, deleted=True):
		cur = scope.get_handle()
		cur.execute("update \"user\" set deleted=%s where iusername=lower(%s)", (deleted, username,))

	def get_user_password(self, scope, username):
		cur = scope.get_handle()
		row = fetch_one(cur, "select password, salt from \"user\" where iusername=lower(%s)", (username,))

		return row[0], row[1]

	def update_user_password(self, scope, username, password, salt):
		cur = scope.get_handle()
		cur.execute("update \"user\" set password=%s, salt=%s where iusername=lower(%s)", (password, salt, username))

	def get_user(self, scope, username):
		cur = scope.get_handle()
		row = fetch_one(cur, "select * from \"user\" where iusername=lower(%s)", (username,))

		user= {}

		for k in ["id", "username", "firstname", "lastname", "email", "gender", "created_on", "avatar", "protected", "blocked", "language"]:
			user[k] = row[k]

		return user

	def remove_password_requests_by_user_id(self, scope, user_id):
		cur = scope.get_handle()
		cur.execute("delete from password_request where user_id=%s", (user_id,))

	def password_request_id_exists(self, scope, id):
		cur = scope.get_handle()

		return execute_scalar(cur, "select count(request_id) from v_password_requests where request_id=%s and datediff<=%s", id, config.PASSWORD_REQUEST_TIMEOUT) > 0

	def create_password_request(self, scope, id, code, user_id):
		cur = scope.get_handle()
		cur.execute("insert into password_request (request_id, request_code, user_id) values (%s, %s, %s)", (id, code, user_id))

	def get_password_request(self, scope, id):
		cur = scope.get_handle()
		row = fetch_one(cur, "select request_id, request_code, username, blocked, deleted " + \
		                     "from v_password_requests " + \
		                     "inner join \"user\" on v_password_requests.user_id=\"user\".id " + \
				     "where request_id=%s and datediff<=%s", id, config.PASSWORD_REQUEST_TIMEOUT)

		request = {"request_id": row["request_id"], "request_code": row["request_code"]}
		request["user"] = {"username": row["username"], "blocked": row["blocked"], "deleted": row["deleted"]}

		return request

	def reset_password(self, scope, id, code, password, salt):
		cur = scope.get_handle()

		if not execute_scalar(cur, "select * from user_reset_password(%s, %s, %s, %s, %s)", id, code, password, salt, config.PASSWORD_REQUEST_TIMEOUT):
			raise exception.InternalFailureException("Password reset failed.")

	def update_user_details(self, scope, username, email, firstname, lastname, gender, language, protected):
		cur = scope.get_handle()
		cur.execute("update \"user\" set email=%s, firstname=%s, lastname=%s, gender=%s, language=%s, protected=%s where iusername=lower(%s)",
		            (email, firstname, lastname, gender, language, protected, username))

	def user_can_change_email(self, scope, username, email):
		cur = scope.get_handle()

		return execute_scalar(cur, "select * from user_can_change_email(%s, %s, %s)", username, email, config.PASSWORD_REQUEST_TIMEOUT)

	def update_avatar(self, scope, username, filename):
		cur = scope.get_handle()
		cur.execute("update \"user\" set avatar=%s where iusername=lower(%s)", (filename, username))

	def get_followed_usernames(self, scope, username):
		cur = scope.get_handle()
		cur.execute("select friends.username from \"user_friendship\" "                           + \
		            "inner join \"user\" as friends on friend_id=friends.id "                     + \
		            "inner join \"user\" as followers on user_id=followers.id "                   + \
		            "where followers.iusername=lower(%s) and friends.deleted=false", (username,))

		friends = []

		for row in cur.fetchall():
			friends.append(row["username"])

		return friends

	def search(self, scope, query):
		if query is None:
			query = re.sub("[^0-9a-zA-Z]+", "_", query)

		sql = "select username from \"user\" where (firstname ilike '%%%s%%' or lastname ilike '%%%s%%' or username ilike '%%%s%%' " \
		      "or iemail like '%%%s%%') and deleted=false order by iusername, firstname, lastname" % (query, query, query, query)

		cur = scope.get_handle()
		cur.execute(sql)

		result = []

		for row in cur.fetchall():
			result.append(row["username"])

		return result

	def is_following(self, scope, user1, user2):
		query = "select count(*) from user_friendship "                                 + \
		        "inner join \"user\" as user_a on user_friendship.user_id=user_a.id "   + \
		        "inner join \"user\" as user_b on user_friendship.friend_id=user_b.id " + \
		        "where user_a.iusername=lower(%s) and user_b.iusername=lower(%s)"

		return execute_scalar(scope.get_handle(), query, user1, user2) > 0

	def follow(self, scope, user1_id, user2_id, follow):
		cur = scope.get_handle()

		if follow:
			cur.execute("insert into user_friendship (user_id, friend_id) values (%s, %s)", (user1_id, user2_id))
		else:
			cur.execute("delete from user_friendship where user_id=%s and friend_id=%s", (user1_id, user2_id))

	def favor(self, scope, user_id, guid, follow=True):
		cur = scope.get_handle()

		if follow:
			cur.execute("insert into user_favorite (user_id, object_guid) values (%s, %s)", (user_id, guid))
		else:
			cur.execute("delete from user_favorite where user_id=%s and object_guid=%s", (user_id, guid))

	def is_favorite(self, scope, user_id, guid):
		cur = scope.get_handle()

		return execute_scalar(cur, "select count(user_id) from user_favorite where user_id=%s and object_guid=%s", user_id, guid) > 0

	def get_favorites(self, scope, user_id):
		query = "select * from v_objects where guid in (select object_guid from user_favorite where user_id=%s)"

		return self.__get_objects__(scope.get_handle(), query, user_id)

	def recommend(self, scope, user_id, receiver_id, guid):
		cur = scope.get_handle()
		cur.execute("insert into user_recommendation (user_id, receiver_id, object_guid) values (%s, %s, %s)", (user_id, receiver_id, guid))

	def recommendation_exists(self, scope, sender, receiver, guid):
		query = "select count(*) from user_recommendation "                                            + \
		        "inner join \"user\" as sender on user_recommendation.user_id=sender.id "              + \
		        "inner join \"user\" as receiver on user_recommendation.receiver_id=receiver.id "      + \
		        "where sender.iusername=lower(%s) and receiver.iusername=lower(%s) and object_guid=%s"

		return execute_scalar(scope.get_handle(), query, sender, receiver, guid) > 0

	def get_recommendations(self, scope, username, page=0, page_size=10):
		recommendations = []
		cur = scope.get_handle()

		for row in fetch_all(cur, "select * from v_recommendations where receiver=lower(%s) order by recommended_on desc offset %s*%s limit %s",
		                           username, page, page_size, page_size):
			details = self.__build_object__(row)
			details["username"] = row["sender"]
			details["recommended_on"] = row["recommended_on"]

			recommendations.append(details)

		return recommendations

class PGObjectDb(PGDb, database.ObjectDb):
	def __init__(self):
		database.UserDb.__init__(self)
		PGDb.__init__(self)

	def create_object(self, scope, guid, source):
		cur = scope.get_handle()
		cur.execute("insert into Object (guid, source) values (%s, %s)", (guid, source))

	def lock_object(self, scope, guid, locked=True):
		cur = scope.get_handle()
		cur.execute("update Object set locked=%s where guid=%s", (locked, guid))

	def is_locked(self, scope, guid):
		return util.to_bool(execute_scalar(scope.get_handle(), "select locked from Object where guid=%s", guid))

	def delete_object(self, scope, guid, deleted=True):
		cur = scope.get_handle()
		cur.execute("update Object set deleted=%s where guid=%s", (deleted, guid))

	def object_exists(self, scope, guid):
		return util.to_bool(execute_scalar(scope.get_handle(), "select count(guid) from Object where guid=%s and deleted=false", guid))

	def get_object(self, scope, guid):
		cur = scope.get_handle()

		row = fetch_one(cur, "select * from v_objects where guid=%s", guid)

		obj = self.__build_object__(row)
		obj["tags"] = self.__get_tags__(cur, guid)

		return obj

	def get_objects(self, scope, page=0, page_size=10):
		query = "select * from v_objects order by created_on desc limit %d offset %d*%d" % (page_size, page, page_size)

		return self.__get_objects__(scope.get_handle(), query)

	def get_tagged_objects(self, scope, tag, page=0, page_size=10):
		return self.__get_objects__(scope.get_handle(), "select * from object_get_tagged(%s) limit %s offset %s*%s", tag, page_size, page, page_size)

	def get_popular_objects(self, scope, page=0, page_size=10):
		query = "select * from v_popular_objects limit %d offset %d*%d" % (page_size, page, page_size)

		return self.__get_objects__(scope.get_handle(), query)

	def get_random_objects(self, scope, page_size=10):
		query = "select * from v_random_objects limit %d" % (page_size)

		return self.__get_objects__(scope.get_handle(), query)

	def add_tag(self, scope, guid, user_id, tag):
		cur = scope.get_handle()

		if execute_scalar(cur, "select count(object_guid) from object_tag where user_id=%s and object_guid=%s and lower(tag)=lower(%s)", user_id, guid, tag) == 0:
			cur.execute("insert into object_tag (user_id, object_guid, tag) values (%s, %s, %s)", (user_id, guid, tag))
		else:
			raise exception.ConflictException("Tag already exists.")

	def get_tags(self, scope):
		tags = []

		for tag in fetch_all(scope.get_handle(), "select * from v_tags"):
			tags.append(to_dict(tag))

		return tags

	def user_can_vote(self, scope, guid, username):
		query = "select count(*) from object_score inner join \"user\" on user_id=id where object_guid=%s and lower(iusername)=lower(%s)"

		return execute_scalar(scope.get_handle(), query, guid, username) == 0

	def vote(self, scope, guid, user_id, up=True):
		scope.get_handle().execute("insert into object_score (user_id, object_guid, up) values (%s, %s, %s)", (user_id, guid, up))

	def get_voting(self, scope, guid, username):
		query = "select up from object_score inner join \"user\" on object_score.user_id=\"user\".id where iusername=lower(%s) and object_guid=%s"

		return execute_scalar(scope.get_handle(), query, username, guid)

	def add_comment(self, scope, guid, user_id, text):
		scope.get_handle().execute("insert into object_comment (user_id, object_guid, comment_text) values (%s, %s, %s)", (user_id, guid, text))

	def flag_comment_deleted(self, scope, id):
		scope.get_handle().execute("update object_comment set deleted=true where id=%s", (id,))

	def get_comments(self, scope, guid, page=0, page_size=100):
		comments = []

		query = "select * from object_get_comments(%s, %s, %s)"

		for row in fetch_all(scope.get_handle(), query, guid, page, page_size):
			comments.append(to_dict(row))

		return comments

	def get_comment(self, scope, id):
		query = "select object_comment.id, comment_text as text, object_comment.created_on, object_comment.deleted, " + \
		        "\"user\".username, object_guid as \"object-guid\" "                                                  + \
			" from object_comment join \"user\" on object_comment.user_id=\"user\".id where object_comment.id=%s"

		return to_dict(fetch_one(scope.get_handle(), query, id))

	def comment_exists(self, scope, id):
		return util.to_bool(execute_scalar(scope.get_handle(), "select count(id) from object_comment where id=%s", id))

	def report_abuse(self, scope, guid):
		cur = scope.get_handle()
		cur.execute("update object set reported=true where guid=%s", (guid,))

class PGStreamDb(PGDb, database.StreamDb):
	def __init__(self):
		database.StreamDb.__init__(self)
		PGDb.__init__(self)

	def get_messages(self, scope, user, limit=100, older_than=None):
		query = "select message.id, target, source, message.created_on, type from message "                + \
		        "inner join \"user\" on \"user\".id=receiver_id "                                          + \
		        "where iusername=lower(%s) and (%s is null or message.created_on<%s) order by created_on " + \
		        "limit %s"

		cur = scope.get_handle()
		messages = []

		for row in fetch_all(cur, query, user, older_than, older_than, limit):
			messages.append(to_dict(row))

		return messages

	def get_public_messages(self, scope, limit=100, older_than=None):
		query = "select id, target, source, created_on, type from public_message " + \
		        "where (%s is null or created_on<%s) order by created_on desc limit %s"

		cur = scope.get_handle()
		messages = []

		for row in fetch_all(cur, query, older_than, older_than, limit):
			messages.append(to_dict(row))

		return messages

class PGMailDb(PGDb, database.MailDb):
	def __init__(self):
		database.MailDb.__init__(self)
		PGDb.__init__(self)

	def push_user_mail(self, scope, subject, body, user_id):
		cur = scope.get_handle()
		cur.execute("insert into mail (subject, body, receiver_id) values (%s, %s, %s)", (subject, body, user_id))

	def push_mail(self, scope, subject, body, mail):
		cur = scope.get_handle()
		cur.execute("insert into mail (subject, body, mail) values (%s, %s, %s)", (subject, body, mail))

	def get_unsent_messages(self, scope, limit=100):
		query = "select mail.id, mail.subject, mail.body, mail.created_on, " + \
		        "coalesce(mail.mail, \"user\".email) as email "              + \
		        "from mail left join \"user\" on receiver_id=\"user\".id "   + \
		        "where sent=false order by created_on, id limit %d" % (limit)

		mails = []
		cur = scope.get_handle()

		for row in fetch_all(cur, query):
			mails.append(to_dict(row))

		return mails

	def mark_sent(self, scope, id):
		cur = scope.get_handle()
		cur.execute("update mail set sent=true where id=%s" % (id,))
