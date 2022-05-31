import time, traceback, sys, json, threading, queue, random, schedule
import util, alsapi
from pathlib import Path
from multiprocessing.connection import Listener
from util import log
from const import *
from timeline import PlayerTimeline
from localtext import trans

class PathyDaemon():
	def __init__(self):
		self.started = False
		self.state = None
		self.last_saved_state = None
		self.stopping = False
		self.worker_tasks = queue.Queue()
		self.timelines = {}
		
		self.statistics = { # TODO TODO TODO
			"started_at": time.time(),
			"ctl_msgs_received": 0,
			"tg_updates_received": 0,
			"state_rewritten": 0,
			"worker_steps": 0,
			"als_api_requests": 0,
			"timeline_entries": 0
		}
		
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
		self.load_state()
		
		self.worker_thread.start()
		self.scheduler_thread.start()
		self.listen_msgs()
		
		# if we are here, softly stopping everything
		log("Stopping daemon")
		self.stopping = True
		self.worker_thread.join(timeout=10)
		if self.worker_thread.is_alive():
			log("Failed to softly stop worker thread, killing")
		else:
			log("Worker thread stopped softly")
		self.unlock()
	
	def listen_msgs(self):
		listener = Listener(DAEMON_ADDR, authkey=DAEMON_AUTHKEY)
		
		running = True
		while running:
			try:
				# strictly 1 request and 1 response per each connection
				conn = listener.accept()
				
				if not conn.poll(5):
					try:
						conn.send("timeout, closing")
					except Exception:
						pass
					raise TimeoutError(
						"Daemon: accepted connection but got no msg")
				
				msg, args = conn.recv()
				if msg == "stop":
					running = False
					conn.send("STOPPING")
					log("Stopping daemon")
				else:
					conn.send(self.handle_msg(msg, args))
				
				conn.close()
			except Exception:
				log(f"Failed to handle daemon command:" \
					f"\n{traceback.format_exc()}", err=True, send_tg=True)
	
	def handle_msg(self, msg, args):
		if msg == "status":
			return self.get_status()
		elif msg == "tgupd":
			self.handle_tg_upd(args.get("tg_upd"))
			return "DONE"
		else:
			return "UNKNOWN_MSG"
	
	def run_worker(self):
		i = 0
		while True:
			try:
				self.handle_tasks()
				self.save_state()
				self.do_worker_step(i)
				self.save_state()
			except Exception:
				log(f"Daemon worker error:\n{traceback.format_exc()}",
					err=True, send_tg=True)
			
			if self.stopping:
				break
			
			time.sleep(10)
			i += 1
	
	def do_worker_step(self, i):
		if not self.timelines: # FIX
			for player_uid in self.state["tracked_players"]:
				self.timelines[player_uid] = PlayerTimeline(player_uid)
		
		# this approach has minor problems while editing player list in runtime
		player_idx = i % len(self.state["tracked_players"])
		player_uid, timeline = list(self.timelines.items())[player_idx] # FIX
		player_stat = alsapi.get_player_stat(player_uid)
		diff = timeline.consume_als_stat(player_stat)
	
	def get_status(self):
		status = {
			"msg_listener_alive": True,
			"worker_thread_alive": self.worker_thread.is_alive(),
			"scheduler_thread_alive": self.scheduler_thread.is_alive(),
			"statistics": self.statistics
		}
		return status
	
	def lock(self):
		try:
			LOCKFILE.unlink(missing_ok=True)
		except Exception as e:
			log("Failed to lock daemon, raising error")
			raise e
		
		self.lock_handle = LOCKFILE.open("w+")
	
	def unlock(self):
		self.lock_handle.close()
	
	def as_worker(self, func, *args, **kwargs):
		self.worker_tasks.put((func, args, kwargs))
	
	def run_scheduler(self):
		def _hour(hour):
			return str(8 - util.get_hours_offset()).zfill(2)
		
		schedule.every().monday.at(f"{_hour(8)}:00").do(
			self.as_worker, self.send_hate_monday_pic)
		schedule.every().hour.at(f":05").do(
			self.as_worker, self.notify_new_videos)
		
		while True:
			try:
				schedule.run_pending()
			except Exception:
				log(f"Failed to execute scheduled task:" \
					f"\n{traceback.foemat_exc()}",
					err=True, send_tg=True)
			time.sleep(1)
	
	def load_state(self):
		if not DAEMON_STATE.exists():
			self.state = {}
			return
		
		state_raw = DAEMON_STATE.read_text(encoding="utf-8")
		self.state = json.loads(state_raw)
	
	def save_state(self):
		self.state["last_save"] = time.time()
		
		state_raw = json.dumps(self.state, indent="\t")
		if state_raw == self.last_saved_state:
			return
		util.safe_file_write(DAEMON_STATE, state_raw)
		self.last_saved_state = state_raw
	
	def handle_tasks(self):
		while self.worker_tasks.qsize():
			try:
				func, args, kwargs = self.worker_tasks.get()
				func(*args, **kwargs)
			except Exception:
				log(f"Daemon worker task executing error:" \
					f"\n{traceback.format_exc()}",
					err=True, send_tg=True)
	
	def handle_tg_upd(self, tg_upd):
		pass # TODO
	
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
	
	def notify_new_videos(self):
		if self.state.get("yt_news") == None:
			self.state["yt_news"] = {}
		
		vids_to_notify = []
		vids = util.get_yt_videos("https://www.youtube.com/c/playapex/videos")
		if not vids:
			raise Exception("Videos list is empty")
		
		for vid_url in vids:
			if not vid_url == self.state["yt_news"].get("last_link"):
				vids_to_notify.append(vid_url)
			else:
				break
		self.state["yt_news"]["last_link"] = vids[0]
		
		vids_to_notify.reverse()
		vids_to_notify = vids_to_notify[-3:]
		for link in vids_to_notify:
			util.call_tg_api(
				"sendMessage", {"chat_id": ASL_CHAT_ID, "text": link})
		
		util.log(f"YT videos check completed: {len(vids_to_notify)} found")


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()