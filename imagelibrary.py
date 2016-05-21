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
#  Import images into the object database.

## @package imagelibrary
#  Import images into the object database.

import config, os, factory, util, mimetypes, logger, cStringIO
from PIL import Image

def import_images():
	log = logger.get_logger()

	log.info("Searching for image files in '%s'", config.IMAGE_LIBRARY_PATH)

	with factory.create_db_connection() as conn:
		db = factory.create_object_db()

		for filename in os.listdir(config.IMAGE_LIBRARY_PATH):
			log.info("Found file: '%s'", filename)

			path = os.path.join(config.IMAGE_LIBRARY_PATH, filename)

			mime = mimetypes.guess_type(path)[0]
			index = filename.rfind(".")
			name = filename[:index]

			b64_origin = os.path.join(config.IMAGE_LIBRARY_BASE64_PATH, "%s.base64" % name)
			b64_thumbnail = os.path.join(config.IMAGE_LIBRARY_BASE64_PATH, "%s.thumbnail.base64" % name)

                        try:
                            if os.path.isfile(path) and (not os.path.exists(b64_origin) or not os.path.exists(b64_thumbnail)):
                                    log.info("Importing file...")

                                    with conn.enter_scope() as scope:
                                            db.create_object(scope, util.new_guid(), filename)

                                            log.info('Creating file: "%s"' % b64_origin)

                                            with open(path, "rb") as f:
                                                    b64 = "data:%s;base64,%s" % (mime, f.read().encode("base64"))

                                            with open(b64_origin, "w") as f:
                                                    f.write(b64)

                                            log.info('Creating file: "%s"' % b64_thumbnail)

                                            image = Image.open(path)
                                            image.thumbnail(config.IMAGE_LIBRARY_THUMBNAIL_SIZE, Image.ANTIALIAS)

                                            buffer = cStringIO.StringIO()
                                            image.save(buffer, "PNG")

                                            b64 = "data:png;base64,%s" % buffer.getvalue().encode("base64")

                                            with open(b64_thumbnail, "w") as f:
                                                    f.write(b64)

                                            scope.complete()
                            else:
                                    log.debug("Ignoring file.")

                        except:
                            dst = os.path.join(config.IMAGE_LIBRARY_FAILURE_PATH, filename)

                            log.error('Import failed, moving file "%s" to "%s"' % (path, dst))

                            os.rename(path, dst)

                            for f in [b64_origin, b64_thumbnail]:
                                try:
                                    log.info('Deleting file: "%s"' % f)
                                    os.remove(f)

                                except:
                                    pass

if __name__ == "__main__":
	import_images()
