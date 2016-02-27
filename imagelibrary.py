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
#  @file imagelibrary.py
#  An image library.

## @package imagelibrary
#  An image library.

import config, os, factory, util, logger
from PIL import Image

def import_images():
	log = logger.get_logger()

	log.info("Searching for image files in '%s'", config.IMAGE_LIBRARY_PATH)

	with factory.create_db_connection() as conn:
		db = factory.create_object_db()

		for filename in os.listdir(config.IMAGE_LIBRARY_PATH):
			log.info("Found file: '%s'", filename)

			path = os.path.join(config.IMAGE_LIBRARY_PATH, filename)
			thumbnail = os.path.join(config.IMAGE_LIBRARY_THUMBNAIL_PATH, filename)

			if os.path.isfile(path) and not os.path.exists(thumbnail):
				log.info("Creating thumbnail: '%s'", thumbnail)

				with conn.enter_scope() as scope:
					db.create_object(scope, util.new_guid(), filename)

					image = Image.open(path)
					image.thumbnail(config.IMAGE_LIBRARY_THUMBNAIL_SIZE, Image.ANTIALIAS)
					image.save(thumbnail)

					scope.complete()
			else:
				log.debug("Ignoring file.")

if __name__ == "__main__":
	import_images()
