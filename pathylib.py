import time, datetime, traceback, os
import util, textutil, alsapi
from pathlib import Path
from util import log, format_time
from const import *
from textutil import trans, get_wish, get_moniker, \
	get_adjectives, get_goodnight_wish


class TrackedPlayer():
	def __init__(self, player_state):
		self.uid = player_state["uid"]
		self.state = player_state
		if not "chats" in self.state:
			self.state["chats"] = {}
		
		self.timeline = StoredTimeline(TIMELINE_DIR / f"{self.uid}.txt")
		self.read_timeline()
	
	def read_timeline(self):
		self.name = self.get_stat("name") or "???"
		self.moniker = self.get_stat("moniker") or "???"
		self.legend = self.get_stat("legend") or "???"
		self.is_online = bool(int(self.get_stat("is_online") or "0"))
		self.is_in_match = bool(int(self.get_stat("is_in_match") or "0"))
		self.is_banned = bool(int(self.get_stat("is_banned") or "0"))
	
	def serialize(self):
		return self.state
	
	def get_rank(self, mode):
		return PlayerRank.from_stat(self.timeline.get_end_stat(), mode=mode)
	
	def get_stat(self, *args):
		return self.timeline.get_stat(*args)
	
	def get_last_sess(self):
		now = int(time.time())
		sess_start = self.get_sess_start(now)
		if sess_start == None:
			return
		sess = self.timeline.get_sub_timeline(sess_start, now)
		return sess
	
	def format_status(self):
		result = f"<b>{self.name}</b>"
		if self.is_online:
			result += f" <i>{self.moniker}</i>"
		result += f"\n<i>{self.format_state()}</i>"
		
		if self.is_online:
			sess = self.get_last_sess()
			if sess:
				result += f"\n<pre>{sess.format(easter_eggs=True)}</pre>"
		
		return result
		
	def format_state(self):
		if not self.is_online:
			last_online = self.get_last_online(time.time())
			offline_duraion = format_time(int(time.time()) - last_online)
			return f"Живе реальним життям вже {offline_duraion}"
		
		state = "В матчі" if self.is_in_match else "В Лобі"
		legend = trans("on_"+self.legend)
		
		state_duration = None
		for entry in self.timeline.iter(reverse=True):
			if entry.stat_name == "is_in_match":
				state_duration = time.time() - entry.timestamp
				break
		
		result = f"{state} на {legend}"
		if state_duration:
			result += f" ({format_time(state_duration)})"
		return result
	
	def gen_new_moniker(self):
		self.moniker = get_moniker()
		moniker_entry = TimelineEntry(
			int(time.time()), "_", "moniker", self.moniker)
		self.timeline.add_entry(moniker_entry)
	
	def update(self):
		upd_resp = {}
		
		self.handle_goodnights()
		
		stat = alsapi.get_player_stat(self.uid)
		diff = self.timeline.consume_als_stat(stat)
		self.read_timeline()
		
		upd_resp["went_online"] = upd_resp["went_offline"] = False
		if diff.get(("_", "is_online")) and diff[("_", "is_online")][0]:
			if diff[("_", "is_online")][1] == "1":
				upd_resp["went_online"] = True
			else:
				upd_resp["went_offline"] = True
		
		if upd_resp["went_online"]:
			self.on_online()
		elif upd_resp["went_offline"]:
			self.on_offline()
		
		upd_resp["got_banned"] = upd_resp["got_unbanned"] = False
		if diff.get(("_", "is_banned")) and diff[("_", "is_banned")][0]:
			if diff[("_", "is_banned")][1] == "1":
				upd_resp["got_banned"] = True
			else:
				upd_resp["got_unbanned"] = True
		
		if upd_resp["got_banned"]:
			self.on_banned()
		elif upd_resp["got_unbanned"]:
			self.on_unbanned()
		
		return upd_resp
	
	def on_online(self):
		self.state["goodnight_at"] = None
		
		last_online = self.get_last_online(time.time())
		# is new session or just break end
		is_new_sess = (time.time() - SESS_MAX_BREAK) > (last_online or 0)
		
		if not is_new_sess:
			for chat_id, chat_state in self.state["chats"].items():
				msg_to_del = chat_state.get("sess_end_msg_id")
				if msg_to_del:
					util.delete_tg_msg(chat_id, msg_to_del)
					chat_state["sess_end_msg_id"] = None
			return
		
		self.gen_new_moniker()
		
		if last_online:
			offline_duraion = format_time(int(time.time()) - last_online)
		else:
			offline_duraion = "довгого"
		
		sess_start_msg = f"🟢 <b>{self.name}</b> тепер " \
			f"<i>{self.moniker}</i>" \
			f" після {offline_duraion} відпочинку\n" \
			f"<i>{get_wish()}</i>"
		
		for chat_id, chat_state in self.state["chats"].items():
			msg_id = self.notify_chat(
				chat_id, sess_start_msg, as_html=True)
			chat_state["sess_end_msg_id"] = None
	
	def on_offline(self):
		hour_local = (time.gmtime().tm_hour + util.get_hours_offset()) % 24
		if hour_local >= 23 or hour_local < 6:
			self.state["goodnight_at"] = int(time.time()) + (60 * 15)
		
		sess = self.get_last_sess()
		if not sess:
			return
		
		sess_end_msg = ""
		sess_end_msg += f"🔴 <b>{self.name}</b> більше не " \
			f"<i>{self.moniker}</i> :(\n"
		sess_end_msg += f"<pre>{sess.format(easter_eggs=True)}</pre>"
		
		for chat_id, chat_state in self.state["chats"].items():
			msg_id = self.notify_chat(chat_id, sess_end_msg,
				as_html=True, silent=True)
			chat_state["sess_end_msg_id"] = msg_id
	
	def on_banned(self):
		adj = get_adjectives()
		ban_reason = self.get_stat("ban_reason") or "🤷‍♂️"
		sec_to_unban = util.to_num(self.get_stat("ban_time_left"))
		unban_after = "🤷‍♂️"
		if sec_to_unban != None:
			unban_after = format_time(sec_to_unban)
		
		notification = f"<b>{self.name}</b> отримав <i>{adj}</i> банан :/\n" \
			f"<i>Причина: {ban_reason}</i>\n" \
			f"<i>Закінчиться через: {unban_after}</i>"
		self.notify_all_chats(notification, as_html=True)
	
	def on_unbanned(self):
		notification = f"У <b>{self.name}</b> нарешті спав банан :)"
		self.notify_all_chats(notification, as_html=True)
	
	def handle_goodnights(self):
		wish_at = self.state.get("goodnight_at")
		if not wish_at:
			return
		if time.time() < wish_at:
			return
		
		wish = get_goodnight_wish(self.name)
		self.notify_all_chats(wish, as_html=True, silent=True)
		self.state["goodnight_at"] = None
	
	def notify_chat(self, chat_id, msg, as_html=False, silent=False):
		sent_msg = util.call_tg_api("sendMessage", {
			"chat_id": chat_id,
			"text": msg,
			"parse_mode": "HTML" if as_html else None,
			"disable_notification": silent
		})
		return sent_msg.get("message_id")
	
	def notify_all_chats(self, msg, as_html=False, silent=False):
		for chat_id, chat_state in self.state["chats"].items():
			self.notify_chat(chat_id, msg, as_html, silent)
	
	def get_last_online(self, before_moment):
		for entry in self.timeline.iter(reverse=True):
			if entry.timestamp > before_moment:
				continue
			if entry.stat_name == "is_online" and entry.stat_value == "0":
				return entry.timestamp
	
	def get_sess_start(self, before_moment):
		sess_start = None
		for entry in self.timeline.iter(reverse=True):
			if entry.timestamp > before_moment:
				continue
			
			if sess_start == None:
				# looking for went online event
				if entry.stat_name == "is_online" and entry.stat_value == "1":
					sess_start = entry.timestamp
			else:
				# looking for any event happened earlier
				# than (sess_start - SESS_MAX_BREAK) or to reset
				# sess_start if another went offline event found earlier
				if entry.timestamp < (sess_start - SESS_MAX_BREAK):
					break
				elif entry.stat_name == "is_online" and \
				entry.stat_value == "0":
					sess_start = None
		
		return sess_start
	
	def add_to_chat(self, chat_id):
		if str(chat_id) not in self.state["chats"]:
			self.state["chats"][str(chat_id)] = {}
	
	def del_from_chat(self, chat_id):
		if str(chat_id) in self.state["chats"]:
			self.state["chats"].pop(str(chat_id))

class Timeline():
	def __init__(self, start_stat=None):
		self._entries = []
		self.start_stat = start_stat or {}
		self.clear_cache()
	
	def clear_cache(self):
		self._cache = {}
	
	def add_entry(self, entry):
		self._entries.append(entry)
		self.clear_cache()
	
	def add_timestamp(self, ts):
		for entry in ts.data.values():
			self.add_entry(entry)
	
	def get_end_stat(self):
		if self._cache.get("end_stat"):
			return self._cache["end_stat"]
		self._cache["end_stat"] = self.start_stat.copy()
		
		for entry in self.iter():
			key = (entry.legend, entry.stat_name)
			self._cache["end_stat"][key] = entry.stat_value
		
		return self._cache["end_stat"]
	
	def get_diff(self):
		if self._cache.get("diff"):
			return self._cache["diff"]
		diff = self._cache["diff"] = {}
		
		for key in self.start_stat:
			if self.start_stat[key] == "$null":
				continue
			diff[key] = (self.start_stat[key], self.start_stat[key])
		
		for entry in self.iter():
			key = (entry.legend, entry.stat_name)
			
			if not diff.get(key):
				diff[key] = (entry.stat_value, entry.stat_value)
				continue
			
			if entry.isnull:
				continue
			
			diff[key] = (diff[key][0], entry.stat_value)
		
		# filtering out equal start-end values
		keys_to_remove = [k for k, v in diff.items() if v[0] == v[1]]
		for key in keys_to_remove:
			diff.pop(key)
		
		return diff
	
	def get_states_duration(self):
		def get_segment_state(seg):
			if isinstance(seg, MatchTimeline):
				if seg.is_real():
					return "inMatch"
				return "inFiringRange"
			
			for ts in seg.iter_timestamps():
				if ts.get_value("is_online") == "0":
					return "offline"
				return "inLobby"
		
		durations = {"offline": 0, "inLobby": 0, "inFiringRange": 0,
			"inMatch": 0}
		
		for seg in self.split_by_states():
			durations[get_segment_state(seg)] += seg.get_duration()
		
		return durations
	
	def iter(self, reverse=False):
		iterable = self._entries
		if reverse:
			iterable = reversed(self._entries)
		
		for entry in iterable:
			yield entry
	
	def iter_timestamps(self, reverse=False):
		cur_ts = None
		for entry in self.iter(reverse=reverse):
			if not cur_ts:
				cur_ts = TimestampStat(entry.timestamp)
			
			if cur_ts.timestamp != entry.timestamp:
				yield cur_ts
				cur_ts = TimestampStat(entry.timestamp)
			
			cur_ts.add_entry(entry)
		
		if cur_ts:
			yield cur_ts
	
	def get_stat(self, *args):
		key = parse_timeline_key(*args)
		return self.get_end_stat().get(key)
	
	def get_sub_timeline(self, start, end):
		start_stat = self.start_stat.copy()
		sub_timeline = None
		
		for entry in self.iter():
			if entry.timestamp < start:
				start_stat[(entry.legend, entry.stat_name)] = entry.stat_value
			elif entry.timestamp > end:
				break
			else:
				if not sub_timeline:
					sub_timeline = Timeline(start_stat)
				sub_timeline.add_entry(entry)
		
		return sub_timeline
	
	def consume_als_stat(self, player_stat):
		timestamp = int(time.time())
		diff_data = {}
		
		def _add(stat_name, stat_value, legend="_"):
			prev_value = self.get_stat(legend, stat_name)
			new_value = str(stat_value)
			if prev_value == new_value:
				return False
			
			entry = TimelineEntry(timestamp, legend, stat_name, stat_value)
			self.add_entry(entry)
			diff_data[(legend, stat_name)] = (prev_value, new_value)
			return True
		
		_global = player_stat["global"]
		_realtime = player_stat["realtime"]
		
		_add("level",  _global["level"] + \
			_global["toNextLevelPercent"] / 100)
		
		_add("is_online", _realtime["isOnline"])
		_add("is_in_match",  _realtime["isInGame"])
		_add("is_banned", int(_global["bans"]["isActive"]))
		_add("ban_reason",    _global["bans"]["last_banReason"])
		_add("ban_time_left", _global["bans"]["remainingSeconds"])
		
		_add("br_rank_score",   _global["rank"]["rankScore"])
		_add("br_rank_div",     _global["rank"]["rankDiv"])
		_add("br_rank_top_pos", _global["rank"]["ladderPosPlatform"])
		_add("br_rank_name",    _global["rank"]["rankName"])
		
		_add("ar_rank_score",   _global["arena"]["rankScore"])
		_add("ar_rank_div",     _global["arena"]["rankDiv"])
		_add("ar_rank_top_pos", _global["arena"]["ladderPosPlatform"])
		_add("ar_rank_name",    _global["arena"]["rankName"])
		
		_add("name", _global["name"])
		selected_legend = player_stat["legends"]["selected"]["LegendName"]
		_add("legend", selected_legend)
		
		legend_trackers = set()
		for tracker in player_stat["legends"]["selected"]["data"]:
			_add("tracker_" + tracker["key"],
				tracker["value"], selected_legend)
			legend_trackers.add("tracker_" + tracker["key"])
		
		# nullifying unavailable trackers (probably unequipped)
		# $null is treated as a special value
		for legend, stat_name in self.get_end_stat():
			if legend != selected_legend: continue
			if not stat_name.startswith("tracker_"): continue
			if stat_name in legend_trackers: continue
			
			_add(stat_name, "$null", selected_legend)
		
		return diff_data
	
	def get_start(self):
		if self._cache.get("start") != None:
			return self._cache["start"]
		
		for entry in self.iter():
			self._cache["start"] = entry.timestamp
			break
		
		return self._cache.get("start")
	
	def get_end(self):
		if self._cache.get("end") != None:
			return self._cache["end"]
		
		for entry in self.iter(reverse=True):
			self._cache["end"] = entry.timestamp
			break
		
		return self._cache.get("end")
	
	def get_duration(self):
		start = self.get_start()
		end = self.get_end()
		if None in [start, end]:
			return 0
		return end - start
	
	def format(self, easter_eggs=False):
		diff = self.get_diff()
		matches = [m for m in self.get_matches() if m.is_real()]
		
		text = ""
		text += f"Час: {format_time(self.get_duration())}\n"
		for state, duration in self.get_states_duration().items():
			if not duration: continue
			text += f"  {trans(state)}: {format_time(duration)}\n"
		if matches:
			text += f"Матчі: {len(matches)}\n"
		
		lvl_diff = diff.get(("_", "level"))
		if lvl_diff:
			text += f"Левел: {lvl_diff[0]} → {lvl_diff[1]}\n"
		
		def _format_rank_diff(mode, caption):
			if not diff.get(("_", f"{mode}_rank_score")):
				return
			before = PlayerRank.from_stat(self.start_stat, mode=mode)
			after  = PlayerRank.from_stat(self.get_end_stat(), mode=mode)
			if before and after:
				return f"{caption}: {before.format()} → {after.format()}\n"
		
		text += _format_rank_diff("br", "Ранг в БР") or ""
		text += _format_rank_diff("ar", "Ранг на Аренах") or ""
		
		legends = {}
		
		# filling matches count to display
		for match in matches:
			legend = match.get_legend()
			if not legend:
				continue
			if not legends.get(legend):
				legends[legend] = {"_matches": 0}
			legends[legend]["_matches"] += 1
		
		# filling all the trackers to display
		for legend, stat_name in diff:
			skip_stats = [
				"tracker_scout_of_action_targets_hit",
				"tracker_jackson_bow_out_damage_done",
				"tracker_smoke_show_damage_done"
			]
			if stat_name in skip_stats:
				continue
			
			if legend == "_" or not stat_name.startswith("tracker_"):
				continue
			if not legend in legends:
				legends[legend] = {}
			
			val_before = util.to_num(diff[(legend, stat_name)][0])
			val_after  = util.to_num(diff[(legend, stat_name)][1])
			if None in (val_before, val_after):
				stat_diff = "???"
			else:
				stat_diff = val_after - val_before
			legends[legend][stat_name[8:]] = stat_diff
		
		for legend, trackers in legends.items():
			text += f"На {trans('on_'+legend)}:\n"
			for tracker, tracker_diff in trackers.items():
				text += f"  {trans(tracker)}: {tracker_diff}"
				
				if easter_eggs and str(tracker_diff).endswith("300"):
					text += "  </pre><span class='tg-spoiler'>" \
						"ВІДСОСИ У КРАБЕРИСТА</span><pre>"
				else:
					text += "\n"
		
		return text.strip()
	
	def split_by_states(self):
		if self._cache.get("state_segs") != None:
			return self._cache["state_segs"]
		segs = self._cache["state_segs"] = []
		sweep_stat = self.start_stat.copy()
		
		def _append_seg(is_match):
			seg_cls = MatchTimeline if is_match else Timeline
			segs.append(seg_cls(sweep_stat.copy()))
		
		_append_seg(sweep_stat.get(("_", "is_in_match")) == "1")
		
		for ts in self.iter_timestamps():
			segs[-1].add_timestamp(ts)
			
			if ts.get_value("level"):
				if isinstance(segs[-1], MatchTimeline):
					segs[-1].result_stamp = segs[-1].result_stamp or ts
				if len(segs) > 1 and isinstance(segs[-2], MatchTimeline):
					segs[-2].result_stamp = segs[-2].result_stamp or ts
			
			if ts.get_value("is_online") or ts.get_value("is_in_match"):
				_append_seg(ts.get_value("is_in_match") == "1")
				segs[-1].add_timestamp(ts)
			
			for key, entry in ts.data.items():
				sweep_stat[key] = entry.stat_value
		
		return segs
	
	def get_matches(self):
		matches = []
		for seg in self.split_by_states():
			if isinstance(seg, MatchTimeline):
				matches.append(seg)
		return matches
	
	def __str__(self):
		return "".join([str(e)+"\n" for e in self.iter()])

class MatchTimeline(Timeline):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		# TimestampStat containing match result stat update
		self.result_stamp = None
	
	def get_end_stat(self):
		end_stat = super().get_end_stat(*args, **kwargs)
		
		if self.result_stamp:
			for key, result_value in self.result_stamp.data.items():
				end_stat[key] = result_value
		
		return end_stat
	
	def get_diff(self, *args, **kwargs):
		diff = super().get_diff(*args, **kwargs)
		
		if self.result_stamp:
			for key, entry in self.result_stamp.data.items():
				if entry.stat_value == "$null":
					continue
				if diff.get(key):
					diff[key] = (diff[key][0], entry.stat_value)
		
		return diff
	
	def get_legend(self):
		legend = self.start_stat.get(("_", "legend"))
		for ts in self.iter_timestamps():
			legend = ts.get_value("legend") or legend
		
		return legend
	
	def is_ended(self):
		for entry in self.iter():
			if entry.stat_name == "is_in_match" and \
			entry.stat_value == "0":
				return True
		return False
	
	def is_real(self):
		# False if match didn't increased level (usually firing range)
		return bool(self.result_stamp)

class StoredTimeline(Timeline):
	def __init__(self, path, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.path = Path(path)
		self.file = self.path.open("ab", buffering=0)
		self.load_file()
	
	def load_file(self):
		self.start_stat = {}
		self.clear_cache()
		
		for entry in self.iter():
			self.add_entry(entry, write_file=False)
	
	def add_entry(self, entry, write_file=True):
		self.clear_cache()
		
		if write_file:
			self.file.seek(0, os.SEEK_END)
			self.file.write(entry.serialize().encode("utf-8") + b"\n")
	
	def iter(self, reverse=False):
		if not self.path.exists():
			return
		
		if reverse:
			iterable = util.reverse_readline(self.path)
		else:
			iterable = self.path.open("r", encoding="utf-8")
		
		try:
			for line in iterable:
				try:
					entry = TimelineEntry.parse(line)
				except TimelineEntryError:
					if line.strip(): # do not report empty lines
						log(f"Skipping invalid entry in"
							f" {self.path.name} timeline: '{line}'\n"
							f"Traceback:\n{traceback.format_exc()}")
					continue
				
				yield entry
		finally:
			if getattr(iterable, "close"):
				iterable.close()
	
	def close(self):
		self.file.close()
	
	def __del__(self):
		self.close()

class TimestampStat():
	def __init__(self, timestamp):
		self.timestamp = int(timestamp)
		self.data = {}
	
	def add_entry(self, entry):
		if not entry.timestamp == self.timestamp:
			raise ValueError
		
		key = (entry.legend, entry.stat_name)
		self.data[key] = entry
	
	def get_entry(self, *args):
		key = parse_timeline_key(*args)
		return self.data.get(key)
	
	def get_value(self, *args):
		key = parse_timeline_key(*args)
		entry = self.data.get(key)
		if entry:
			return entry.stat_value


class TimelineEntry():
	def __init__(self, timestamp, legend, stat_name, stat_value):
		self.timestamp = timestamp
		self.legend = legend
		self.stat_name = stat_name
		self.stat_value = stat_value
		self.stat_value_num = util.to_num(self.stat_value)
		self.isnull = self.stat_value == "$null"
	
	@classmethod
	def parse(cls, entry_line):
		entry = entry_line.strip(" \r\n")
		entry_split = entry.split(" ")
		
		if len(entry_split) != 4:
			raise TimelineEntryError("Invalid number of entry chunks")
		
		entry_split[0] = util.to_num(entry_split[0])
		entry_split[1] = util.semiurldecode(str(entry_split[1]))
		entry_split[2] = util.semiurldecode(str(entry_split[2]))
		entry_split[3] = util.semiurldecode(str(entry_split[3]))
		
		if entry_split[0] == None:
			raise TimelineEntryError("Invalid entry timestamp")
		
		return cls(*entry_split)
	
	def serialize(self):
		return " ".join((
			str(self.timestamp),
			util.semiurlencode(str(self.legend)),
			util.semiurlencode(str(self.stat_name)),
			util.semiurlencode(str(self.stat_value))
		))
	
	def __str__(self):
		return self.serialize()

class TimelineEntryError(ValueError):
	pass

class PlayerRank():
	def __init__(self, score, div, top_pos, rank_name, mode):
		self.score = score
		self.div = div
		self.top_pos = top_pos
		self.rank_name = rank_name
		self.mode = mode
	
	def format(self):
		points_name = "RP" if self.mode == "br" else "AP"
		
		if self.rank_name == "Apex Predator":
			return f"{trans(self.rank_name)} #{self.top_pos}"
		if self.rank_name == "Master":
			return f"{trans(self.rank_name)} ({self.score}{points_name})"
		
		rank_div_scores = {
			"br": [
				0, 250, 500, 750,
				1000, 1500, 2000, 2500,
				3000, 3600, 4200, 4800,
				5400, 6100, 6800, 7500,
				8200, 9000, 9800, 10600,
				11400, 12300, 13200, 14100,
				15000
			],
			"ar": [
				0, 400, 800, 1200,
				1600, 2000, 2400, 2800,
				3200, 3600, 4000, 4400,
				4800, 5200, 5600, 6000,
				6400, 6800, 7200, 7600,
				8000
			]
		}
		
		next_percentage = util.calc_mid_percentage(
			self.score, rank_div_scores[self.mode])
		return f"{trans(self.rank_name)} {self.div} ({next_percentage}%)"
	
	def __str__(self):
		return self.format()
	
	@classmethod
	def from_stat(cls, stat, mode):
		args = [
			util.to_num(stat.get(("_", f"{mode}_rank_score"))),
			util.to_num(stat.get(("_", f"{mode}_rank_div"))),
			util.to_num(stat.get(("_", f"{mode}_rank_top_pos"))),
			stat.get(("_", f"{mode}_rank_name"))
		]
		if None in args:
			return None
		
		return cls(*args, mode)

def format_map(mode_name, mapinfo):
	cur_map  = trans(mapinfo["current"]["map"])
	next_map = trans(mapinfo["next"]["map"])
	cur_map_time  = format_time(mapinfo["current"]["remainingSecs"])
	next_map_time = format_time(mapinfo["next"]["DurationInSecs"])
	
	result = f"<b>{mode_name}</b> зараз на карті <b>{cur_map}</b>\n"
	result += f"<i>Через {cur_map_time} перейде на "
	if mapinfo["next"]["map"] == "Unknown":
		result += f"іншу карту</i>"
	else:
		result += f"<b>{next_map}</b>, де буде {next_map_time}</i>"
	return result

def format_map_rotation():
	maps = alsapi.get_map_rotation()
	delim = "\n--- --- ---\n"
	
	return delim.join((
		format_map("БР",           maps["battle_royale"]),
		format_map("Ранкед БР",    maps["ranked"]),
		format_map("Арена",        maps["arenas"]),
		format_map("Ранкед арена", maps["arenasRanked"])
	))

def parse_timeline_key(*args):
	if len(args) == 1:
		if isinstance(args[0], tuple):
			key = args[0]
		else:
			key = ("_", args[0])
	elif len(args) == 2:
		key = (args[0], args[1])
	else:
		raise ValueError("Invalid arguments number")
	
	return key