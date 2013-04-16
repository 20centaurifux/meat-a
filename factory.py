# -*- coding: utf-8 -*-

import config, mongodb

def create_db_util():
	return mongodb.MongoDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)

def create_user_db():
	return mongodb.MongoUserDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)

def create_object_db():
	return mongodb.MongoObjectDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)

def create_stream_db():
	return mongodb.MongoStreamDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)

def create_mail_db():
	return mongodb.MongoMailDb(config.MONGODB_DATABASE, config.MONGODB_HOST, config.MONGODB_PORT)
