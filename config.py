# -*- coding: utf-8 -*-

WEBSITE_URL              = "http://localhost:8000"

TEMPLATE_DIR             = "tpl"

MONGODB_HOST             = "127.0.0.1"
MONGODB_PORT             = 27017
MONGODB_DATABASE         = "meata"

LANGUAGES                = [ "en", "de" ]

REQUEST_EXPIRY_TIME      = 60

USER_REQUEST_TIMEOUT     = 600
PASSWORD_REQUEST_TIMEOUT = 600
PASSWORD_RESET_TIMEOUT   = 600
DEFAULT_EMAIL_LIFETIME   = 7200
REQUEST_CODE_LENGTH      = 128
DEFAULT_PASSWORD_LENGTH  = 8

UPLOAD_DIR               = "upload"
TMP_DIR                  = "tmp"

AVATAR_MAX_FILESIZE      = 1024 * 1024
AVATAR_MAX_WIDTH         = 180
AVATAR_MAX_HEIGHT        = 180
AVATAR_FORMATS           = [ "JPEG", "PNG", "GIF" ]
AVATAR_EXTENSIONS        = [ ".jpg", ".jpeg", ".png", ".gif" ]
AVATAR_DIR               = "images\users"

WSGI_MAX_REQUEST_LENGTH  = 1024 * 1024
