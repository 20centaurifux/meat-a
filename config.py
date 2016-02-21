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
#  @file config.py
#  Configuration settings.

## @package config
#  Configuration settings.

## Application REALM.
REALM                     = "meat-a"

## URL of the website.
WEBSITE_URL               = "http://localhost:8000"

## Directory where to find template files.
TEMPLATE_DIR              = "tpl"

## Hostname of the PSQL server.
PG_HOST = "127.0.0.1"
## PSQL port.
PG_PORT = 5432
## PSQL database name.
PG_DB   = "meat-a"
## PSQL user account.
PG_USER = "meat-a"
## PSQL password.
PG_PWD  = "123456"

## Languages supported by the application.
LANGUAGES                 = ["en"]
## Default language.
DEFAULT_LANGUAGE          = "en"

## Specifies how long a timestamp sent within a request is valid (in seconds).
REQUEST_EXPIRY_TIME       = 60

## Specifies how long a request code for a user account is valid (in seconds).
USER_REQUEST_TIMEOUT      = 600
## Specifies how long a request code for a new password is valid (in seconds).
PASSWORD_REQUEST_TIMEOUT  = 600
## Specifies the lifetime of a reset password email in the mail queue (in seconds).
PASSWORD_RESET_TIMEOUT    = 600
## Specifies the default lifetime of emails in the mail queue (in seconds).
DEFAULT_EMAIL_LIFETIME    = 7200
## Length of generated request ids.
REQUEST_ID_LENGTH         = 32
## Length of generated request codes.
REQUEST_CODE_LENGTH       = 32
## Length of generated passwords.
DEFAULT_PASSWORD_LENGTH   = 8
## Length of generated passwords.
PASSWORD_SALT_LENGTH      = 32

## Location for storing temporary files.
TMP_DIR                   = "tmp"

## Maximum file size of avatar images (in bytes).
AVATAR_MAX_FILESIZE       = 1048576
## Maximum width allowed for avatar images.
AVATAR_MAX_WIDTH          = 180
## Maximum height allowed for avatar images.
AVATAR_MAX_HEIGHT         = 180
## Allowed avatar image formats.
AVATAR_FORMATS            = ["JPEG", "PNG", "GIF"]
## Allowed avatar file extensions (always use lower case).
AVATAR_EXTENSIONS         = [".jpg", ".jpeg", ".png", ".gif"]
## Location for uploaded images.
AVATAR_DIR                = "images/users"

## Maximum HTTP request length.
WSGI_MAX_REQUEST_LENGTH   = 1048704

## Enable to limit HTTP requests from the same IP address.
LIMIT_REQUESTS            = True
## Number of allowed user account requests per hour from the same IP address.
ACCOUNT_REQUESTS_PER_HOUR = 15
## Number of allowed reset password requests per hour from the same IP address.
PASSWORD_RESETS_PER_HOUR  = 5
## Number of allowed HTTP requests per hour from the same IP address.
REQUESTS_PER_HOUR         = 1800

## IP address where the mailer should listen.
MAILER_HOST               = "127.0.0.1"
## Port of the mailer.
MAILER_PORT               = 9797
## Array storing IP addresses of clients which are allowed to send PING requests to the mailer.
MAILER_ALLOWED_CLIENTS    = ["127.0.0.1"]
## The UDP timeout.
MAILER_UDP_TIMEOUT        = 5
## Defines when the mailer checks for new mails automatically (in seconds).
MAIL_CHECK_INTERVAL       = 60

## A SMTP server.
SMTP_HOST                 = ""
## Port of the configured SMTP server.
SMTP_PORT                 = 25
## True to enable SSL.
SMTP_SSL                  = False
## Address of a SMTP user.
SMTP_ADDRESS              = ""
## Username of a SMTP user.
SMTP_USERNAME             = ""
## Password of the configured SMTP user.
SMTP_PASSWORD             = ""
