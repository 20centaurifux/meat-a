# -*- coding: utf-8 -*-

from rocket import Rocket
from wsgi import index

if __name__ == "__main__":
	server = Rocket(("127.0.0.1", 8000), "wsgi", { "wsgi_app": index })
	server.start()
