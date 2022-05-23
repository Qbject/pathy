import time, traceback, sys, util
from pathlib import Path
from multiprocessing.connection import Listener

class PathyDaemon():
	def __init__(self):
		self.listener_address = ("localhost", 6914)
		self.listener_authkey = b"***REMOVED***"
	
	def start(self):
		listener = Listener(self.listener_address, authkey=self.listener_authkey)
		
		running = True
		while running:
			# strictly 1 request and 1 response per 1 connection
			conn = listener.accept()
			msg = conn.recv()
			util.log(msg)
			conn.send(f"echo: {msg}")
			
			if msg == "stop":
				running = False
			conn.close()


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()