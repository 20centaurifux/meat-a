import abc

class UserDb(object):
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def get_user(self, username): return None

	@abc.abstractmethod
	def search_user(self, query): return None

	@abc.abstractmethod
	def create_user(self, username, email, firstname, lastname, password, gender): return

	@abc.abstractmethod
	def update_user_details(self, username, email, firstname, lastname, gender): return

	@abc.abstractmethod
	def update_user_password(self, username, password): return

	@abc.abstractmethod
	def get_user_password(self, username): return None

	@abc.abstractmethod
	def block_user(self, username, blocked): return

	@abc.abstractmethod
	def user_is_blocked(self, username): return

	@abc.abstractmethod
	def update_avatar(self, username, avatar): return

	@abc.abstractmethod
	def user_exists(self, username): return False

	@abc.abstractmethod
	def email_assigned(self, email): return False

	@abc.abstractmethod
	def user_request_code_exists(self, code): return False

	@abc.abstractmethod
	def remove_user_request(self, code): return

	@abc.abstractmethod
	def create_user_request(self, username, email, code): return

	@abc.abstractmethod
	def username_requested(self, username): return False

class ObjectDb(object):
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def create_object(self, guid, source): return

	@abc.abstractmethod
	def lock_object(self, guid): return

	@abc.abstractmethod
	def is_locked(self, guid): return False

	@abc.abstractmethod
	def remove_object(self, guid): return

	@abc.abstractmethod
	def get_object(self, guid): return None

	@abc.abstractmethod
	def get_objects(self, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def get_popular_objects(self, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def get_random_objects(self, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def add_tags(self, guid, tags): return

	@abc.abstractmethod
	def rate(self, guid, username, up = True): return

	@abc.abstractmethod
	def user_can_rate(self, guid, username): return False

	@abc.abstractmethod
	def add_comment(self, guid, username, text): return

	@abc.abstractmethod
	def get_comments(self, guid, page = 0, page_size = 10): return None

	@abc.abstractmethod
	def favor_object(self, guid, username, favor = True): return

	@abc.abstractmethod
	def is_favorite(self, guid, username): return False

	@abc.abstractmethod
	def get_favorites(self, username, page = 0): return None
