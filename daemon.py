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
			try:
				# strictly 1 request and 1 response per each connection
				conn = listener.accept()
				
				if not conn.poll(5):
					conn.send("timeout, closing")
					raise TimeoutError(
						"Daemon: accepted connection but got no msg")
				
				msg, args = conn.recv()
				util.log(msg)
				conn.send(f"ECHO\n{msg = }\n{args = }")
				
				if msg == "stop":
					running = False
				conn.close()
			except Exception:
				util.log(f"Failed to handle daemon command:" \
					f"\n{traceback.format_exc()}", err=True, send_tg=True)
	
	def sync_state(self): # TODO: mechanism of preventing a few daemons running on same state simultneously (some field that increments every sync)
		"""
		universal method for reading and writing state
		to/from disk depending on different conditions
		"""
		
		if (not DAEMON_STATE.exists()) and (not self.state):
			self.state = {}
		
		if self.state:
			self.state.last_sync = time.time()
			
			state_raw = json.dumps(self.state, indent="\t")
			util.safe_file_write(DAEMON_STATE, state_raw)
		else:
			state_raw = DAEMON_STATE.read_text(encoding="utf-8")
			self.state = json.loads(state_raw)
		


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()