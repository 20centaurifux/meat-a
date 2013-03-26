import config, mongodb

def create_db_util():
	return mongodb.MongoDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)

def create_user_db():
	return mongodb.MongoUserDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)

def create_object_db():
	return mongodb.MongoObjectDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)
