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

WEBSITE_URL               = "http://localhost:8000"

TEMPLATE_DIR              = "tpl"

MONGODB_HOST              = "127.0.0.1"
MONGODB_PORT              = 27017
MONGODB_DATABASE          = "meata"

LANGUAGES                 = [ "en", "de" ]

REQUEST_EXPIRY_TIME       = 60

USER_REQUEST_TIMEOUT      = 600
PASSWORD_REQUEST_TIMEOUT  = 600
PASSWORD_RESET_TIMEOUT    = 600
DEFAULT_EMAIL_LIFETIME    = 7200
REQUEST_CODE_LENGTH       = 128
DEFAULT_PASSWORD_LENGTH   = 8

UPLOAD_DIR                = "upload"
TMP_DIR                   = "tmp"

AVATAR_MAX_FILESIZE       = 1024 * 1024
AVATAR_MAX_WIDTH          = 180
AVATAR_MAX_HEIGHT         = 180
AVATAR_FORMATS            = [ "JPEG", "PNG", "GIF" ]
AVATAR_EXTENSIONS         = [ ".jpg", ".jpeg", ".png", ".gif" ]
AVATAR_DIR                = "images\users"

WSGI_MAX_REQUEST_LENGTH   = 1024 * 1024

LIMIT_REQUESTS            = True
ACCOUNT_REQUESTS_PER_HOUR = 15
PASSWORD_RESETS_PER_HOUR  = 5
REQUESTS_PER_HOUR         = 1800

MAILER_HOST               = "127.0.0.1"
MAILER_PORT               = 9797
MAILER_ALLOWED_CLIENTS    = [ "127.0.0.1" ]
MAILER_UDP_TIMEOUT        = 5
MAIL_CHECK_INTERVAL       = 60
