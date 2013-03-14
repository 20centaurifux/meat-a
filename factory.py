import config, mongodb

def create_user_db():
	return mongodb.MongoUserDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)
