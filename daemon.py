import time, traceback, sys, json, threading, queue, random, schedule
import util, alsapi, tgapi
from pathlib import Path
from multiprocessing.connection import Listener
from util import log
from const import *
from pathylib import TrackedPlayer, format_map_rotation
from textutil import trans, fix_text_layout, get_moniker

class PathyDaemon():
	def __init__(self):
		self.started = False
		self.state = None
		self.stopping = False
		self.worker_tasks = queue.Queue()
		self.players_online_count = None
		self.worker_cycle = 0
		
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
			self.state["player_fetch_delay"] = int(args.get("delay", 2))
		elif msg == "tgupd":
			self.as_worker(self.handle_tg_upd, args.get("upd_body"))
			return "DONE"
		elif msg == "segments":
			player = self.get_player_by_uid(args.get("uid"))
			sess_segs = player.get_last_sess().split_by_states()
			return "\n--- --- ---\n".join([seg.format() for seg in sess_segs])
		else:
			return "UNKNOWN_MSG"
	
	def run_worker(self):
		while True:
			try:
				if (self.worker_cycle % 2) == 0:
					self.do_player_upd(self.worker_cycle / 2)
				elif (self.worker_cycle % 2) == 1:
					self.handle_cmds()
				self.save_state()
			except Exception:
				log(f"Daemon worker error:\n{traceback.format_exc()}",
					err=True, send_tg=True)
			
			if self.stopping:
				break
			
			util.cap_freq("worker_cycle", 0.1)
			self.worker_cycle += 1
	
	def do_player_upd(self, i):
		util.cap_freq("player_upd", self.state.get("player_fetch_delay", 2))
		
		try:
			# this approach is inconsistent if
			# player list is updated in runtime
			players_count = len(self.state["tracked_players"])
			
			if players_count:
				player_idx = int((i / 2) % players_count)
				player = self.state["tracked_players"][player_idx]
				upd_resp = player.update()
				if upd_resp["went_online"] or upd_resp["went_offline"]:
					self.handle_party_events(player)
		except Exception as e:
			log(f"Player '{player.name}' update error, throttling\n" +
				traceback.format_exc(), err=True, send_tg=True)
			time.sleep(10)
	
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
			caption = f"{players_online} <i>{get_moniker(plural=True)}</i>!"
			
			sent_msg = tgapi.call(
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
		result += f"{'Живий' if self.worker_thread.is_alive() else '😵'}"
		result += f" (циклів: {self.worker_cycle})\n"
		result += f"Потік планувальника: "
		result += f"{'Живий' if self.scheduler_thread.is_alive() else '😵'}\n"
		
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
		if DAEMON_STATE.exists():
			state_raw = DAEMON_STATE.read_text(encoding="utf-8")
			state = json.loads(state_raw)
			
			if state["tracked_players"]:
				for i, player_state in enumerate(state["tracked_players"]):
					state["tracked_players"][i] = TrackedPlayer(player_state)
			
			self.state = state
		else:
			self.state = {}
		
		if not "tracked_players" in self.state:
			self.state["tracked_players"] = []
		if not "chats_data" in self.state:
			self.state["chats_data"] = {}
	
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
	
	def get_player_by_uid(self, uid):
		for player in self.iter_players():
			if str(player.uid) == uid:
				return player
	
	def get_player_by_name(self, name):
		for player in self.iter_players():
			if player.name == name:
				return player
	
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
			if not upd.is_whitelisted():
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
		
		if bot_cmd == "/status":
			statuses = [player.format_status() for \
				player in self.iter_players(in_chat=upd.chat_id)]
			delim = "\n--- --- ---\n"
			upd.reply(delim.join(statuses), as_html=True)
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
		
		tgapi.call(
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
			tgapi.call(
				"sendMessage", {"chat_id": ASL_CHAT_ID, "text": link})
		
		util.log(f"YT videos check completed: {len(vids_to_notify)} found")


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		daemon = PathyDaemon()
		daemon.start()