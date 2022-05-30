import time, traceback, sys, json, asyncio, threading, queue, random, schedule
import util, alsapi
from pathlib import Path
from multiprocessing.connection import Listener
from util import log
from const import *
from timeline import PlayerStatTimeline

class PathyDaemon():
	def __init__(self):
		self.started = False
		self.state = None
		self.stopping = False
		self.worker_signals = queue.Queue()
		self.timelines = {}
		
		self.worker_thread = threading.Thread(
			target=self.run_worker, daemon=True)
		self.scheduler_thread = threading.Thread(
			target=self.run_scheduler, daemon=True)
	
	def start(self):
		if self.started:
			raise RuntimeError("Daemon object can be started only once")
		self.started = True
		
		log("Starting daemon")
		self.lock()
		
		self.worker_thread.start()
		self.scheduler_thread.start()
		self.listen_actions()
		
		# if we are here, softly stopping everything
		log("Stopping daemon")
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
		i = 0
		while True:
			try:
				self.sync_state()
				self.handle_signals()
				self.do_worker_step(i)
			except Exception:
				log(f"Daemon worker error:\n{traceback.format_exc()}",
					err=True, send_tg=True)
			
			if self.stopping:
				break
			
			time.sleep(1)
			i += 1
	
	def do_worker_step(self, i):
		if not self.timelines:
			for player_uid in self.state["tracked_players"]:
				self.timelines[player_uid] = PlayerStatTimeline(player_uid)
		
		# this approach has minor problems while editing player list in runtime
		player_idx = i % len(self.state["tracked_players"])
		player_uid, timeline = self.timelines.items()[player_idx]
		player_stat = alsapi.get_player_stat(player_uid)
		diff = timeline.consume_als_stat(player_stat)
	
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
		def _hour(hour):
			return str(8 - util.get_hours_offset()).zfill(2)
		
		def _test():
			util.call_tg_api(
				"sendMessage",
				{
					"chat_id": DEBUG_CHAT_ID,
					"text": "hey",
					"parse_mode": "HTML"
				}
			)
		
		schedule.every().monday.at(f"{_hour(8)}:00").do(
			self.send_hate_monday_pic)
		schedule.every().hour.at(":00").do(_test)
		
		while True:
			try:
				schedule.run_pending()
			except Exception:
				log(f"Failed to execute scheduled task:" \
					f"\n{traceback.foemat_exc()}",
					err=True, send_tg=True)
			time.sleep(1)
	
	def sync_state(self):
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
	
	def send_hate_monday_pic(self):
		monday_ing_id = "AgACAgIAAx0CTJBx5QADHWEiP2LrqUGngEIIOJ4BNUHmVk_" \
		"4AAJntTEboQ8RSVxQerfln3yYAQADAgADeQADIAQ"
		
		util.call_tg_api(
			"sendPhoto",
			{
				"chat_id": ASL_CHAT_ID,
				"photo": monday_ing_id,
				"parse_mode": "HTML",
				"disable_notification": True
			}
		)


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()