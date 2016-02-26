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

import config, pgdb, smtp

## Creates a database.Connection instance.
def create_db_connection():
	return pgdb.PGConnection(config.PG_DB, host=config.PG_HOST, port=config.PG_PORT, username=config.PG_USER, password=config.PG_PWD)

## Creates a database.TestDb instance.
def create_test_db():
	return pgdb.PGTestDb()

## Creates a database.UserDb instance.
def create_user_db():
	return pgdb.PGUserDb()

## Creates a database.ObjectDb instance.
def create_object_db():
	return pgdb.PGObjectDb()

## Creates a database.StreamDb instance.
def create_stream_db():
	return pgdb.PGStreamDb()

## Creates a database.MailDb instance.
def create_mail_db():
	return pgdb.PGMailDb()

## Creates a database.RequestDb instance.
def create_request_db():
	return pgdb.PGRequestDb()

## Creates a mailer.MTA instance.
def create_mta():
	return smtp.SMTP_MTA(config.SMTP_HOST, config.SMTP_PORT, config.SMTP_SSL, config.SMTP_ADDRESS, config.SMTP_USERNAME, config.SMTP_PASSWORD)
