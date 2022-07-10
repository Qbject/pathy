import time, sys, json, threading, random, schedule
import util, alsapi, tgapi
from pathlib import Path
from multiprocessing.connection import Listener
from collections import deque
from util import log, get_err
from const import *
from pathylib import TrackedPlayer, format_map_rotation
from textutil import trans, fix_text_layout, get_moniker, get_count_moniker

class PathyDaemon():
	def __init__(self):
		self.started = False
		self.state = None
		self.last_updated_player = None
		
		self.main_worker  = WorkerThread("main",  daemon=True)
		self.fetch_worker = WorkerThread("fetch", daemon=True)
		self.scheduler = threading.Thread(
			target=self.run_scheduler, daemon=True)
	
	def start(self):
		if MAINTAINANCE_MODE:
			raise RuntimeError("Daemon cannot be started during maintainance")
		if self.started:
			raise RuntimeError("Daemon object can only be started once")
		self.started = True
		
		log("Starting daemon")
		self.lock()
		self.load_state()
		
		self.main_worker.start()
		self.fetch_worker.start()
		self.scheduler.start()
		self.run_listener()
	
	def stop(self):
		try:
			log("Stopping daemon")
			
			try:
				self.main_worker.stop(timeout=10)
				log("Main worker stopped gracefully")
			except TimeoutError:
				log("Failed to gracefully stop main worker, killing")
			try:
				self.fetch_worker.stop(timeout=10)
				log("Fetch worker stopped gracefully")
			except TimeoutError:
				log("Failed to gracefully stop fetch worker, killing")
			
			self.save_state()
			self.unlock()
		except Exception:
			log(f"Daemon stopping error:\n{get_err()}", err=True)
	
	def run_listener(self):
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
				if msg == "stop": running = False
				conn.send(self.handle_cmd(msg, args))
				conn.close()
			except Exception:
				log(f"Failed to handle daemon command:" \
					f"\n{get_err()}",
					err=True, send_tg=True)
	
	def handle_cmd(self, msg, args):
		if msg == "stop":
			self.stop()
			return "STOPPED"
		
		if msg == "status":
			return self.get_status()
		
		if msg == "setdelay":
			self.state["player_fetch_delay"] = int(args.get("delay", 2))
			return True
		
		if msg == "tgupd":
			self.main_worker.task(self.handle_tg_upd).run(args.get("upd_body"))
			return "DONE"
		
		if msg == "segments":
			player = self.get_player_by_uid(args.get("uid", "1007161381428"))
			sess_segs = player.get_last_sess().split_by_states()
			return "\n--- --- ---\n".join([seg.format() for seg in sess_segs])
		
		if msg == "format_players":
			result = ""
			for player in self.iter_players():
				result += f"[{player.uid}]: {player.name}\n"
				result += "Chats:\n"
				for chat_id in player.state["chats"]:
					chat_state = self.get_chat_state(chat_id)
					result += f"  [{chat_id}]: {chat_state.get('title')}\n"
				result += "\n"
			return f"<pre>{util.sanitize_html(result.strip())}</pre>"
		
		if msg == "whitelist":
			added = self.whitelist_chat(args.get("chat_id"))
			return "Added" if added else "Already whitelisted"
		
		if msg == "unwhitelist":
			removed = self.unwhitelist_chat(args.get("chat_id"))
			return "Removed" if removed else "Already unwhitelisted"
		
		if msg == "monikers":
			return "\n".join([get_moniker() for i in range(args.get("n", 5))])
		
		else:
			return "UNKNOWN_MSG"
	
	def _get_player_to_upd(self):
		# This approach is inconsistent if player list is updated in runtime
		players = self.state["tracked_players"]
		if not players:
			return
		
		if self.last_updated_player in players:
			idx = (players.index(self.last_updated_player) + 1) % len(players)
		else:
			idx = 0
		
		self.last_updated_player = players[idx]
		return players[idx]
	
	def do_player_upd(self):
		"""
		Uses main worker to get player to update, then retrieves player
		statistics from ALS API using fetch worker (to not to slow down main
		worker with web requests), then runs update on retrieved data on
		main worker
		"""
		player = self.main_worker.task(
			self._get_player_to_upd, sync=True).run()
		if not player: return
		
		def _fetch_step():
			stat = alsapi.get_player_stat(player.uid)
			self.main_worker.task(_update_step).run(stat)
		
		def _update_step(stat):
			upd_resp = player.update(stat)
			if upd_resp["went_online"] or upd_resp["went_offline"]:
				self.handle_party_events(player)
		
		try:
			self.fetch_worker.task(
				_fetch_step, max=1, tag="stat_fetch").run()
		except OverflowError:
			pass
		# fetch_thread = threading.Thread(target=_fetch_step, daemon=True)
		# fetch_thread.start()
	
	def handle_party_events(self, player):
		for chat_id in player.state["chats"]:
			chat_state = self.get_chat_state(chat_id)
			msg_to_del = chat_state.get("last_party_msg_id")
			if msg_to_del:
				tgapi.delete_msg(chat_id, msg_to_del)
				chat_state["last_party_msg_id"] = None
			
			players_online = len(list(self.iter_players(
				online=True, in_chat=chat_id)))
			img = util.get_party_img(players_online)
			if not img: continue
			caption = f"<i>{get_count_moniker(players_online)}</i>!"
			
			sent_msg = tgapi.send_message(chat_id, caption, as_html=True,
				file_path=img, file_type="photo")
			chat_state["last_party_msg_id"] = sent_msg.get("message_id")
	
	def get_chat_state(self, chat_id):
		if not str(chat_id) in self.state["chats_data"]:
			self.state["chats_data"][str(chat_id)] = {}
		return self.state["chats_data"][str(chat_id)]
	
	def get_status(self):
		result = ""
		result += f"Головний потік: "
		result += f"{'Живий' if True else '😵'}\n"
		result += f"Робочий потік: "
		result += f"{'Живий' if self.main_worker.is_alive() else '😵'}\n"
		result += f"Потік отримання стати: "
		result += f"{'Живий' if self.fetch_worker.is_alive() else '😵'}\n"
		result += f"Потік планувальника: "
		result += f"{'Живий' if self.scheduler.is_alive() else '😵'}\n"
		
		return result.strip()
	
	def lock(self):
		try:
			DAEMON_LOCKFILE.unlink(missing_ok=True)
		except Exception as e:
			log("Failed to lock daemon, raising error")
			raise e
		
		self.lock_handle = DAEMON_LOCKFILE.open("w+")
	
	def unlock(self):
		self.lock_handle.close()
	
	def run_scheduler(self):
		def _hour(hour):
			return str(hour - util.get_hours_offset()).zfill(2)
		
		schedule.every().monday.at(f"{_hour(8)}:00").do(
			lambda: self.main_worker.task(self.send_hate_monday_pic).run())
		schedule.every().hour.at(":05").do(
			lambda: self.main_worker.task(self.notify_new_videos).run())
		
		updater_interval = self.state.get("player_fetch_delay", 2)
		schedule.every(updater_interval).seconds.do(self.do_player_upd)
		schedule.every(5).seconds.do(
			lambda: self.main_worker.task(self.save_state).run())
		
		while True:
			try:
				schedule.run_pending()
			except Exception:
				log(f"Failed to execute scheduled task:" \
					f"\n{get_err()}",
					err=True, send_tg=True)
			time.sleep(1)
	
	def load_state(self):
		self.state = util.get_state()
		
		if not "tracked_players" in self.state:
			self.state["tracked_players"] = []
		if not "chats_data" in self.state:
			self.state["chats_data"] = {}
		if not "whitelisted_chats" in self.state:
			self.state["whitelisted_chats"] = []
		
		for i, player_state in enumerate(self.state["tracked_players"]):
			self.state["tracked_players"][i] = TrackedPlayer(player_state)
	
	def save_state(self):
		def _serialize(item):
			if type(item) == TrackedPlayer:
				return item.serialize()
		
		self.state["last_save"] = time.time()
		
		state_raw = json.dumps(self.state, indent="\t", default=_serialize)
		util.write_file_with_retries(DAEMON_STATE,      state_raw)
		util.write_file_with_retries(DAEMON_STATE_COPY, state_raw)
	
	def iter_players(self, online=False, in_chat=None):
		for player in self.state["tracked_players"]:
			if online and not player.is_online:
				continue
			if in_chat and not str(in_chat) in player.state["chats"]:
				continue
			yield player
	
	def get_player_by_uid(self, uid):
		for player in self.iter_players():
			if str(player.uid) == uid:
				return player
	
	def get_player_by_name(self, name):
		for player in self.iter_players():
			if player.name == name:
				return player
	
	def whitelist_chat(self, chat_id):
		chat_id = str(chat_id)
		if chat_id in self.state["whitelisted_chats"]:
			return False
		self.state["whitelisted_chats"].append(chat_id)
		return True
	
	def unwhitelist_chat(self, chat_id):
		chat_id = str(chat_id)
		if chat_id not in self.state["whitelisted_chats"]:
			return False
		self.state["whitelisted_chats"].remove(chat_id)
		return True
	
	def add_tracked_player(self, player_uid, chat_id):
		player = self.get_player_by_uid(player_uid)
		if player:
			player.add_to_chat(chat_id)
			return
		
		player = TrackedPlayer({
			"uid": str(player_uid),
			"chats": {
				str(chat_id): {}
			}
		})
		self.state["tracked_players"].append(player)
	
	def del_tracked_player(self, player_uid, chat_id):
		player = self.get_player_by_uid(player_uid)
		if not player:
			return
		
		player.del_from_chat(chat_id)
		if not player.state["chats"]:
			self.state["tracked_players"].remove(player)
	
	def handle_tg_upd(self, body_raw):
		upd = tgapi.Update.from_raw_body(body_raw)
		
		if upd.is_msg():
			if not util.is_chat_whitelisted(upd.chat_id):
				log(f"Non-whitelisted TG msg:\n{upd.format()}", send_tg=True)
				return
			try:
				self.handle_tg_msg(upd)
			except Exception as e:
				upd.reply("Тут якась діч, хз що з цим робити :(")
				raise e
		else:
			log(f"Unrecognized TG update:\n{upd.format()}", send_tg=True)
	
	def handle_tg_msg(self, upd):
		chat_state = self.get_chat_state(upd.chat_id)
		bot_cmd, bot_cmd_args = upd.parse_bot_command()
		
		if (not bot_cmd) and upd.chat_id == DEBUG_CHAT_ID:
			upd.reply(upd.format(as_html=True), as_html=True)
		
		chat_state["title"] = upd.get_chat_title()
		chat_state["type"] = upd.data["message"]["chat"]["type"]
		
		if bot_cmd == "/status":
			statuses = [player.format_status() for \
				player in self.iter_players(in_chat=upd.chat_id)]
			delim = "\n--- --- ---\n"
			upd.reply(delim.join(statuses) or "Немає грунів :(", as_html=True)
			return
		
		if bot_cmd == "/maps":
			upd.reply(format_map_rotation(), as_html=True)
			return
		
		if bot_cmd == "/fuck":
			targ_txt = bot_cmd_args
			if upd.reply_to:
				if upd.reply_to.get("text"):
					targ_txt = upd.reply_to["text"]
				if upd.reply_to.get("caption"):
					targ_txt = upd.reply_to["caption"]
			
			if targ_txt.strip():
				result = util.sanitize_html(fix_text_layout(targ_txt))
				resp = f"<i>{result}</i>"
			else:
				resp = "Потрібно писати з реплаєм на повідомлення " \
					"або типу:\n<b>/fuck Afr wtq vfhcsfycmrbq</b>"
			
			upd.reply(resp, as_html=True)
			return
		
		if bot_cmd == "/online":
			online_in_chat = 0
			for player in self.iter_players(online=True, in_chat=upd.chat_id):
				online_in_chat += 1
				upd.reply_img(util.get_legend_img(player.legend), \
					player.format_status(), as_html=True)
			
			if not online_in_chat:
				tumbleweed_vid = ASSETS_DIR / "tumbleweed.mkv"
				upd.reply_vid(tumbleweed_vid, "Немає грунів :(")
			return
		
		if bot_cmd == "/addplayer":
			sent_msg = upd.reply(
				"Юзернейм груна (Origin):",
				reply_to_message_id=upd.msg_id,
				reply_markup='{"force_reply": true, "selective": true}'
			)
			
			chat_state["addplayer_msg_id"] = sent_msg.get("message_id")
			chat_state["addplayer_initiator"] = upd.from_id
			return
		
		if bot_cmd == "/delplayer":
			kbrd = [[p.name] for p in self.iter_players(in_chat=upd.chat_id)]
			sent_msg = upd.reply(
				"Ок, кому тут більше не місце?",
				reply_to_message_id=upd.msg_id,
				reply_markup=json.dumps({
					"keyboard": [["Забий, не треба нікого видаляти"]] + kbrd,
					"one_time_keyboard": True,
					"selective": True
				})
			)
			
			chat_state["delplayer_msg_id"] = sent_msg.get("message_id")
			chat_state["delplayer_initiator"] = upd.from_id
			return
		
		reply_to_id = upd.reply_to["message_id"] if upd.reply_to else None
		if reply_to_id and (reply_to_id == chat_state.get("addplayer_msg_id")):
			if chat_state["addplayer_initiator"] != upd.from_id:
				return
			
			player_name = upd.text
			player_uid = alsapi.name_to_uid(player_name)
			self.add_tracked_player(player_uid, upd.chat_id)
			upd.reply(f"Ок, <b>{util.sanitize_html(player_name)}" \
				f"</b>, я за тобою слідкую 👀", as_html=True)
			chat_state["addplayer_msg_id"] = None
			chat_state["addplayer_initiator"] = None
			return
		
		if reply_to_id and (reply_to_id == chat_state.get("delplayer_msg_id")):
			if chat_state["delplayer_initiator"] != upd.from_id:
				return
			
			if upd.text == "Забий, не треба нікого видаляти":
				upd.reply(f"Ну не треба так не треба 🤷‍♂️", \
					reply_markup='{"remove_keyboard": true}')
				return
			
			player = self.get_player_by_name(upd.text)
			if not player: return
			self.del_tracked_player(player.uid, upd.chat_id)
			upd.reply(f"Ок, не знаю більше ніякого " \
				f"<b>{util.sanitize_html(player.name)}</b>", \
				as_html=True, reply_markup='{"remove_keyboard": true}')
			chat_state["delplayer_msg_id"] = None
			chat_state["delplayer_initiator"] = None
			return
	
	def send_hate_monday_pic(self):
		monday_img_id = "AgACAgIAAx0CTJBx5QADHWEiP2LrqUGngEIIOJ4BNUHmVk_" \
		"4AAJntTEboQ8RSVxQerfln3yYAQADAgADeQADIAQ"
		
		tgapi.send_message(ASL_CHAT_ID, as_html=True,
			file_id=monday_img_id, file_type="photo")
	
	def notify_new_videos(self):
		if self.state.get("yt_news") == None:
			self.state["yt_news"] = {}
		
		vids_to_notify = []
		vids = util.get_yt_videos("https://www.youtube.com/c/playapex/videos")
		if not vids:
			raise ValueError("Video list is empty")
		
		for vid_url in vids:
			if not vid_url == self.state["yt_news"].get("last_link"):
				vids_to_notify.append(vid_url)
			else:
				break
		self.state["yt_news"]["last_link"] = vids[0]
		
		vids_to_notify.reverse()
		vids_to_notify = vids_to_notify[-3:]
		for link in vids_to_notify:
			tgapi.send_message(ASL_CHAT_ID, link)

class WorkerThread(threading.Thread):
	def __init__(self, name=None, daemon=False):
		super().__init__(daemon=daemon)
		self.name = name
		self._tasks = deque()
		self._idle = threading.Lock()
	
	def run(self):
		while True:
			if self._tasks:
				task = self._tasks.popleft()
				
				try:
					if util.equal_functions(task.func, self._stop_identifier):
						break
					
					task.result = task.func(*task.args, **task.kwargs)
					if task.then: task.then()
				
				except Exception as e:
					task.err = e
					log(f"Worker '{self.name}' error:\n{get_err()}",
						err=True, send_tg=True)
				
				finally:
					if task.lock:
						task.lock.release()
			else:
				self._idle.acquire()
				self._idle.acquire()
				self._idle.release()
	
	def task(self, func, *args, **kwargs):
		return WorkerTask(self, func, *args, **kwargs)
	
	def do_task(self, task):
		if not self.is_alive():
			raise RuntimeError(f"Worker thread {self.name} is dead")
		
		if task.max:
			same_tasks = len(list(filter(
				lambda prev_task: prev_task.tag == task.tag, self._tasks)))
			if same_tasks >= task.max:
				raise OverflowError(f"Daemon worker queue limit reached " \
					f"for task with tag {task.tag}")
		
		self._tasks.append(task)
		if self._idle.locked():
			self._idle.release()
		
		if task.sync:
			if not task.lock.acquire(timeout=task.timeout):
				raise TimeoutError
			task.lock.release()
			
			if task.err: raise task.err
			return task.result
	
	def stop(self, drop_pending=False, timeout=10):
		if drop_pending:
			self._tasks.clear()
		self.task(self._stop_identifier, sync=True, timeout=timeout).run()
	
	def _stop_identifier(self):
		pass

class WorkerTask():
	def __init__(self, thread, func, sync=False,
			max=0, tag=None, then=None, timeout=-1):
		if max and not tag:
			raise ValueError("Specifying tag is required if max is provided")
		if (timeout > 0) and not sync:
			raise ValueError("Timeout param is only applicable in sync mode")
		
		self.thread = thread
		self.func = func
		self.sync = sync
		self.max = max
		self.tag = tag
		self.then = then
		self.timeout = timeout
		
		self.invoked = False
		self.result = None
		self.err = None
		
		self.lock = None
		if self.sync:
			self.lock = threading.Lock()
			self.lock.acquire()
	
	def run(self, *args, **kwargs):
		if self.invoked:
			raise RuntimeError("Worker task can be invoked only once")
		self.invoked = True
		
		self.args = args
		self.kwargs = kwargs
		return self.thread.do_task(self)


if __name__ == "__main__":
	daemon = PathyDaemon()
	daemon.start()