import time, traceback, sys, util, json, asyncio
from pathlib import Path
from multiprocessing.connection import Listener
from const import *

class PathyDaemon():
	def __init__(self):
		self.state = None
	
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
	
	def sync_state(self):
		"""
		universal method for reading and writing state
		to|from disk depending on different conditions
		"""
		
		if (not self.state) and (not DAEMON_STATE.exists()):
			self.state = {}
		elif not self.state:
			state_raw = DAEMON_STATE.read_text(encoding="utf-8")
			self.state = json.loads(state_raw)
		else:
			state_raw = json.dumps(self.state, indent="\t")
			util.safe_file_write(DAEMON_STATE, state_raw)


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()