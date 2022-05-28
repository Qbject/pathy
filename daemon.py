import time, traceback, sys, util, json, asyncio, threading, schedule, queue, random
from pathlib import Path
from multiprocessing.connection import Listener
from util import log
from const import *

class PathyDaemon():
	def __init__(self):
		self.state = None
		self.stopping = False
		self.worker_signals = queue.Queue()
		
		self.worker_thread = threading.Thread(
			target=self.run_worker, daemon=True)
		self.scheduler_thread = threading.Thread(
			target=self.run_scheduler, daemon=True)
	
	def start(self):
		self.lock()
		
		self.worker_thread.start()
		self.scheduler_thread.start()
		self.listen_actions()
		
		# if we are here, softly stopping everything
		log("Stopping")
		self.stopping = True
		self.worker_thread.join(timeout=10)
		if self.worker_thread.is_alive():
			log("Failed to softly stop worker thread, killing")
		else:
			log("Worker thread stopped softly")
		self.unlock()
	
	def listen_actions(self):
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
				log(msg)
				conn.send(f"ECHO\n{msg = }\n{args = }")
				
				if msg == "stop":
					running = False
				conn.close()
			except Exception:
				log(f"Failed to handle daemon command:" \
					f"\n{traceback.format_exc()}", err=True, send_tg=True)
	
	def run_worker(self):
		while True:
			try:
				self.handle_signals()
				
				
				
				self.sync_state()
			except Exception:
				log(f"Daemon worker error:\n{traceback.format_exc()}",
					err=True, send_tg=True)
			
			if self.stopping:
				break
			
			time.sleep(1)
	
	def lock(self):
		try:
			LOCKFILE.unlink(missing_ok=True)
		except Exception as e:
			log("Failed to lock daemon, raising error")
			raise e
		
		self.lock_handle = LOCKFILE.open("w+")
	
	def unlock(self):
		self.lock_handle.close()
	
	def run_scheduler(self):
		pass
	
	def sync_state(self): # TODO: mechanism of preventing a few daemons running on same state simultneously (some field that increments every sync)
		"""
		universal method for reading and writing state
		to/from disk depending on different conditions
		"""
		
		if (not DAEMON_STATE.exists()) and (not self.state):
			self.state = {}
		
		if self.state != None:
			self.state["last_sync"] = time.time()
			
			state_raw = json.dumps(self.state, indent="\t")
			util.safe_file_write(DAEMON_STATE, state_raw)
		else:
			state_raw = DAEMON_STATE.read_text(encoding="utf-8")
			self.state = json.loads(state_raw)
	
	def handle_signals(self):
		while self.worker_signals.qsize():
			try:
				signal, params = self.worker_signals.get()
				
				
			except Exception:
				log(f"Daemon worker signal handling error:" \
					f"\n{traceback.format_exc()}",
					err=True, send_tg=True)


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()