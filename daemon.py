import time, traceback, sys, json, threading, queue, random, schedule
import util, alsapi
from pathlib import Path
from multiprocessing.connection import Listener
from util import log
from const import *
from pathylib import TrackedPlayer, format_map_rotation
from textutil import trans, marsian_to_ua, get_moniker

class PathyDaemon():
	def __init__(self):
		self.started = False
		self.state = None
		self.stopping = False
		self.worker_tasks = queue.Queue()
		self.players_online_count = None
		
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
					conn.send(self.handle_cmd(msg, args))
				
				conn.close()
			except Exception:
				log(f"Failed to handle daemon command:" \
					f"\n{traceback.format_exc()}",
					err=True, send_tg=True)
	
	def handle_cmd(self, msg, args):
		if msg == "status":
			return self.get_status()
		elif msg == "setdelay":
			self.state["player_fetch_delay"] = int(args.get("delay", 1))
		elif msg == "tgupd":
			self.handle_tg_upd(args.get("upd_body"))
			# self.as_worker(self.handle_tg_upd, args.get("upd_body"))
			return "DONE"
		else:
			return "UNKNOWN_MSG"
	
	def run_worker(self):
		i = 0
		while True:
			try:
				self.do_worker_step(i)
				self.save_state()
			except Exception:
				log(f"Daemon worker error:\n{traceback.format_exc()}",
					err=True, send_tg=True)
			
			if self.stopping:
				break
			
			i += 1
	
	def do_worker_step(self, i):
		if (i % 2) == 0:
			# this approach is inconsistent if
			# player list is updated in runtime
			players_count = len(self.state["tracked_players"])
			if players_count:
				player_idx = int((i / 2) % players_count)
				player = self.state["tracked_players"][player_idx]
				#player.update(verbose=(str(player.uid) == "1007161381428"))
				player.update(verbose=False)
				if player.last_update_result.get("started_new_sess"):
					self.on_new_online(player)
					
			time.sleep(self.state.get("player_fetch_delay", 1))
		elif (i % 2) == 1:
			self.handle_cmds()
	
	def on_new_online(self, player):
		for chat_id in player.state["chats"]:
			players_online = len(list(self.iter_players(
				online=True, in_chat=chat_id)))
			img = util.get_party_img(players_online)
			if not img: continue
			caption = f"{players_online} <i>{get_moniker(plural=True)}</i>!"
			
			util.call_tg_api(
				"sendPhoto",
				{
					"chat_id": chat_id,
					"photo": "attach://file",
					"parse_mode": "HTML",
					"caption": caption
				},
				files={
					"file": img.open("rb")
				}
			)
	
	def get_status(self):
		result = ""
		
		result += f"Головний потік: " \
			f"{'Живий' if True else '😵'}\n"
		result += f"Робочий потік: " \
			f"{'Живий' if self.worker_thread.is_alive() else '😵'}\n"
		result += f"Потік планувальника: " \
			f"{'Живий' if self.scheduler_thread.is_alive() else '😵'}\n"
		
		return result.strip()
	
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
			return str(hour - util.get_hours_offset()).zfill(2)
		
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
			self.state = {"tracked_players": []}
			return
		
		state_raw = DAEMON_STATE.read_text(encoding="utf-8")
		state = json.loads(state_raw)
		
		if state["tracked_players"]:
			for i, player_state in enumerate(state["tracked_players"]):
				state["tracked_players"][i] = TrackedPlayer(player_state)
		
		self.state = state
	
	def save_state(self):
		def _serialize(item):
			if type(item) == TrackedPlayer:
				return item.serialize()
		
		self.state["last_save"] = time.time()
		
		state_raw = json.dumps(self.state, indent="\t", default=_serialize)
		util.safe_file_write(DAEMON_STATE, state_raw)
	
	def handle_cmds(self):
		while self.worker_tasks.qsize():
			try:
				func, args, kwargs = self.worker_tasks.get()
				func(*args, **kwargs)
			except Exception:
				log(f"Daemon worker task executing error:" \
					f"\n{traceback.format_exc()}",
					err=True, send_tg=True)
	
	def iter_players(self, online=False, in_chat=None):
		for player in self.state["tracked_players"]:
			if online and not player.is_online:
				continue
			if in_chat and not str(in_chat) in player.state["chats"]:
				continue
			yield player
	
	def handle_tg_upd(self, body_raw):
		update = util.TgUpdate.from_raw_body(body_raw)
		if not update.is_msg():
			return
		if not update.is_whitelisted():
			return
		
		delim = "\n--- --- ---\n"
		chat_id = update.data["message"]["chat"]["id"]
		bot_cmd, bot_cmd_args = update.parse_bot_command()
		
		if (not bot_cmd) and chat_id == DEBUG_CHAT_ID:
			update.reply(f"<pre>{update.format()}</pre>", as_html=True)
		
		if bot_cmd == "/status":
			resp = ""
			for player in self.iter_players(in_chat=chat_id):
				resp += player.format_status() + delim
			
			if resp.endswith(delim):
				resp = resp[:-len(delim)]
			update.reply(resp.strip(), as_html=True)
		
		elif bot_cmd == "/maps":
			update.reply(format_map_rotation(), as_html=True)
		
		elif bot_cmd == "/fuck":
			targ_txt = ""
			if update.data["message"].get("reply_to_message"):
				targ_msg = update.data["message"]["reply_to_message"]
				if targ_msg.get("text"):
					targ_txt = targ_msg["text"]
			else:
				targ_txt = bot_cmd_args
			
			if targ_txt.strip():
				resp = f"<i>{util.html_sanitize(marsian_to_ua(targ_txt))}</i>"
			else:
				resp = "Потрібно писати з реплаєм на повідомлення " \
					"або типу:\n<b>/fuck Afr wtq vfhcsfycmrbq</b>"
			
			update.reply(resp, as_html=True)
		
		elif bot_cmd == "/online":
			online_in_chat = 0
			for player in self.iter_players(online=True, in_chat=chat_id):
				online_in_chat += 1
				util.call_tg_api(
					"sendPhoto",
					{
						"chat_id": chat_id,
						"photo": "attach://file",
						"parse_mode": "HTML",
						"caption": player.format_status()
					},
					files={
						"file": util.get_legend_img(player.legend).open("rb")
					}
				)
			
			if not online_in_chat:
				update.reply("Немає грунів :(")
	
	def send_hate_monday_pic(self):
		monday_img_id = "AgACAgIAAx0CTJBx5QADHWEiP2LrqUGngEIIOJ4BNUHmVk_" \
		"4AAJntTEboQ8RSVxQerfln3yYAQADAgADeQADIAQ"
		
		util.call_tg_api(
			"sendPhoto",
			{
				"chat_id": ASL_CHAT_ID,
				"photo": monday_img_id,
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