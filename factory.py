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
"""

##
#  @file factory.py
#  Various factory functions.

## @package factory
#  Various factory functions.

import config, mongodb, pqdb, pymongo, smtp

# Creates a database.Connection instance.
def create_db_connection():
	return pqdb.PQConnection(config.PQ_DB, host=config.PQ_HOST, port=config.PQ_PORT, username=config.PQ_USER, password=config.PQ_PWD)

## Creates a database.TestDb instance.
def create_test_db():
	return pqdb.TestDb()

## Creates a database.UserDb instance.
def create_user_db():
	return pqdb.PQUserDb()

## Creates a database.ObjectDb instance.
def create_object_db():
	return pqdb.PQObjectDb()

## Creates a database.StreamDb instance.
def create_stream_db():
	return pqdb.PQStreamDb()

## Creates a database.MailDb instance.
def create_mail_db():
	return pqdb.PQMailDb()
