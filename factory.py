# -*- coding: utf-8 -*-

import config, mongodb, pymongo

def create_db_util():
	return mongodb.MongoDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

def create_user_db():
	return mongodb.MongoUserDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

def create_shared_user_db(client):
	return mongodb.MongoUserDb(config.MONGODB_DATABASE, client = client)

def create_object_db():
	return mongodb.MongoObjectDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

def create_shared_object_db(client):
	return mongodb.MongoObjectDb(config.MONGODB_DATABASE, client = client)

def create_stream_db():
	return mongodb.MongoStreamDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

def create_shared_stream_db(client):
	return mongodb.MongoStreamDb(config.MONGODB_DATABASE, client = client)

def create_mail_db():
	return mongodb.MongoMailDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

def create_shared_client():
	return pymongo.MongoClient(config.MONGODB_HOST, config.MONGODB_PORT)
