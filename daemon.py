import time, traceback, sys, util
from pathlib import Path
from multiprocessing.connection import Listener
from const import *

class PathyDaemon():
	def __init__(self):
		pass
	
	def start(self):
		listener = Listener(DAEMON_ADDR, authkey=DAEMON_AUTHKEY)
		
		running = True
		while running:
			# strictly 1 request and 1 response per each connection
			conn = listener.accept()
			msg, args = conn.recv()
			util.log(msg)
			conn.send(f"ECHO\n{msg = }\n{args = }")
			
			if msg == "stop":
				running = False
			conn.close()


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()