import database, psycopg2, psycopg2.extras, re, util

class PQTransactionScope(database.TransactionScope):
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

	return cur.fetchone()

class PQConnection(database.Connection):
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
		return PQTransactionScope(self)

	def cursor(self, factory=psycopg2.extras.DictCursor):
		return self.__conn.cursor(cursor_factory=factory)

	def commit(self):
		self.__conn.commit()

	def rollback(self):
		self.__conn.rollback()

	def close(self):
		if self.__conn is not None:
			self.__conn.close()

class PQUserDb(database.UserDb):
	def __init__(self):
		database.UserDb.__init__(self)

	def user_request_id_exists(self, scope, id):
		return util.to_bool(execute_scalar(scope.get_handle(), "select count(request_id) from user_request where request_id=%s", id))

	def get_user_request(self, scope, id):
		return fetch_one(scope.get_handle(), "select request_id, request_code, username, email, created_on from user_request where request_id=%s", (id, ))

	def username_or_email_assigned(self, scope, username, email):
		return util.to_bool(execute_scalar(scope.get_handle(), "select user_name_or_email_assigned(%s, %s)", username, email))

	def create_user_request(self, scope, id, code, username, email):
		cur = scope.get_handle()
		cur.execute("insert into user_request (request_id, request_code, username, email) values (%s, %s, %s, %s)", (id, code, username, email))

	def activate_user(self, scope, id, code, password, salt):
		id = execute_scalar(scope.get_handle(), "select * from user_activate(%s, %s, %s, %s)", id, code, password, salt)

		if id is None:
			raise exception.UserActivationFailed()

		return id

	def user_exists(self, scope, username):
		return util.to_bool(execute_scalar(scope.get_handle(), "select count(id) from \"user\" where iusername=lower(%s)", username))

	def user_is_blocked(self, scope, username):
		return util.to_bool(execute_scalar(scope.get_handle(), "select blocked from \"user\" where iusername=lower(%s)", username))

	def block_user(self, scope, username, blocked):
		cur = scope.get_handle()
		cur.execute("update \"user\" set blocked=%s where iusername=lower(%s)", (blocked, username,))

	def delete_user(self, scope, username, deleted):
		cur = scope.get_handle()
		cur.execute("update \"user\" set deleted=%s where iusername=lower(%s)", (deleted, username,))

	def get_user_password(self, scope, username):
		row = fetch_one(scope.get_handle(), "select password, salt from \"user\" where iusername=lower(%s)", (username,))

		return row[0], row[1]

	def update_user_password(self, scope, username, password, salt):
		cur = scope.get_handle()
		cur.execute("update \"user\" set password=%s, salt=%s where iusername=lower(%s)", (password, salt, username))

	def get_user(self, scope, username):
		row = fetch_one(scope.get_handle(), "select * from \"user\" where iusername=lower(%s)", (username,))

		user= {}

		for k in row.keys():
			if k not in ["iusername", "iemail"]:
				user[k] = row[k]

			user["username"] = row["iusername"]
			user["email"] = row["iemail"]

		return user

	def remove_password_requests_by_user_id(self, scope, user_id):
		cur = scope.get_handle()
		cur.execute("delete from password_request where user_id=%s", (user_id,))

	def password_request_id_exists(self, scope, id):
		return util.to_bool(execute_scalar(scope.get_handle(), "select count(request_id) from password_request where request_id=%s", id))

	def create_password_request(self, scope, id, code, user_id):
		cur = scope.get_handle()
		cur.execute("insert into password_request (request_id, request_code, user_id) values (%s, %s, %s)", (id, code, user_id))

	def get_password_request(self, scope, id):
		row = fetch_one(scope.get_handle(), "select request_id, request_code, username, blocked, deleted from password_request "
		                                    "inner join \"user\" on password_request.user_id=\"user\".id")

		request = {"request_id": row["request_id"], "request_code": row["request_code"]}
		request["user"] = {"username": row["username"], "blocked": row["blocked"], "deleted": row["deleted"]}

		return request

	def reset_password(self, scope, id, code, password, salt):
		if not util.to_bool(execute_scalar(scope.get_handle(), "select * from user_reset_password(%s, %s, %s, %s)", id, code, password, salt)):
			raise PasswordResetFailed()

	def update_user_details(self, scope, username, email, firstname, lastname, gender, language, protected):
		cur = scope.get_handle()
		cur.execute("update \"user\" set email=%s, firstname=%s, lastname=%s, gender=%s, language=%s, protected=%s where iusername=lower(%s)",
		            (email, firstname, lastname, gender, language, protected, username))

	def user_can_change_email(self, scope, username, email):
		return util.to_bool(execute_scalar(scope.get_handle(), "select * from user_can_change_email(%s, %s)", username, email))

	def update_avatar(self, scope, username, filename):
		cur = scope.get_handle()
		cur.execute("update \"user\" set avatar=%s where iusername=lower(%s)", (filename, username))

	def get_user(self, scope, username):
		return fetch_one(scope.get_handle(), "select * from \"user\" where iusername=lower(%s)", username)

	def get_followed_usernames(self, scope, username):
		cur = scope.get_handle()
		cur.execute("select friends.username from \"user_friendship\" "
		            "inner join \"user\" as friends on friend_id=friends.id "
		            "inner join \"user\" as followers on user_id=followers.id "
		            "where followers.iusername=lower(%s) and friends.deleted=false", (username,))

		friends = []

		for row in cur.fetchmany():
			friends.append(row["username"])

		return friends

	def search(self, scope, query):
		if query is None:
			query = re.sub("[^0-9a-zA-Z]+", "_", query)

		cur = scope.get_handle()
		cur.execute("select iusername from \"user\" "
		            "where firstname ilike '%%%s%%' or lastname ilike '%%%s%%' or iusername like '%%%s%%' "
		            "or iemail like '%%%s%%' and deleted=false order by iusername, firstname, lastname" % (query, query, query, query))

		result = []

		for row in cur.fetchmany():
			result.append(row["iusername"])

		return result
