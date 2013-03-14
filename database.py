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
