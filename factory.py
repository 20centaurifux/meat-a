# -*- coding: utf-8 -*-
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

	This synchronziation procedure works only file-based. It will not upload
	empty folders or remove empty folders on the remote site.
"""

##
#  @file factory.py
#  Various factory functions.

## @package factory
#  Various factory functions.

import config, mongodb, pymongo

## Creates a database.DbUtil instance.
def create_db_util():
	return mongodb.MongoDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

## Creates a database.UserDb instance.
def create_user_db():
	return mongodb.MongoUserDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

## Creates a database.UserDb instance using a shared connecion.
#  @param client a shared connection
def create_shared_user_db(client):
	return mongodb.MongoUserDb(config.MONGODB_DATABASE, client = client)

## Creates a database.ObjectDb instance.
def create_object_db():
	return mongodb.MongoObjectDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

## Creates a database.ObjectDb instance using a shared connection.
#  @param client a shared connection
def create_shared_object_db(client):
	return mongodb.MongoObjectDb(config.MONGODB_DATABASE, client = client)

## Creates a database.StreamDb instance.
def create_stream_db():
	return mongodb.MongoStreamDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

## Creates a database.StreamDb instance using a shared client.
#  @param client a shared connection
def create_shared_stream_db(client):
	return mongodb.MongoStreamDb(config.MONGODB_DATABASE, client = client)

## Creates a database.MailDb instance.
def create_mail_db():
	return mongodb.MongoMailDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

## Creates a database.MailDb instance using a shared client.
#  @param client a shared connection
def create_shared_mail_db(client):
	return mongodb.MongoMailDb(config.MONGODB_DATABASE, client = client)

## Creates a database.RequestDb instance.
def create_request_db():
	return mongodb.MongoRequestDb(config.MONGODB_DATABASE, host = config.MONGODB_HOST, port = config.MONGODB_PORT)

## Creates a database.RequestDb instance using a shared client.
#  @param client a shared connection
def create_shared_request_db(client):
	return mongodb.MongoRequestDb(config.MONGODB_DATABASE, client = client)

## Creates a connection instance which can be shared by multiple data stores.
def create_shared_client():
	return pymongo.MongoClient(config.MONGODB_HOST, config.MONGODB_PORT)
