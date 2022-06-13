import time, datetime
import util, textutil, alsapi
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
		
		self.timeline = PlayerTimeline(self.uid)
		self.read_timeline()
	
	def read_timeline(self):
		self.name = self.get_stat("name") or "???"
		self.moniker = self.get_stat("moniker") or "???"
		self.legend = self.get_stat("legend") or "???"
		self.cur_state = self.get_stat("cur_state") or "???"
		self.is_online = bool(int(self.get_stat("is_online") or "0"))
		self.is_banned = bool(int(self.get_stat("is_banned") or "0"))
	
	def serialize(self):
		return self.state
	
	def get_rank(self, mode):
		return PlayerRank.from_stat(self.timeline.cur_stats, mode=mode)
	
	def get_stat(self, stat_name, legend="_"):
		return self.timeline.cur_stats.get((legend, stat_name))
	
	def format_status(self):
		result = f"<b>{self.name}</b>"
		if self.is_online:
			result += f" <i>{self.moniker}</i>\n"
			result += f"<i>{self.format_state()}</i>"
		result += "\n"
		
		if self.is_online:
			now = int(time.time())
			sess_start = self.timeline.get_sess_start(now)
			if sess_start == None:
				return
			sess = self.timeline.get_segment(sess_start, now)
			result += f"<pre>{sess.format(easter300=True)}</pre>"
		
		else:
			last_online = self.timeline.get_last_online(time.time())
			offline_duraion = format_time(int(time.time()) - last_online)
			result += f"<i>Вже {offline_duraion} як зайнятий " \
				f"більш корисними справами, ніж Апекс</i>"
		
		return result
		
	def format_state(self):
		state = trans(self.cur_state)
		legend = trans("on_"+self.legend)
		state_duration = format_time(
			time.time() - int(self.get_stat("state_since") or "0"))
		
		return f"{state} на {legend} ({state_duration})"
	
	def gen_new_moniker(self):
		self.moniker = get_moniker()
		moniker_entry = TimelineEntry(
			int(time.time()), "_", "moniker", self.moniker)
		self.timeline.add_entry(moniker_entry)
	
	def update(self, verbose=False):
		self.handle_goodnights()
		
		stat = alsapi.get_player_stat(self.uid)
		diff = self.timeline.consume_als_stat(stat)
		self.read_timeline()
		
		if verbose and diff:
			msg = f"{self.name}:\n"
			for (legend, stat_name), (before, after) in diff.items():
				if legend != "_":
					msg += f"({legend}) "
				msg += f"{stat_name}: {before} -> {after}\n"
			log(msg, send_tg=True)
		
		went_online = went_offline = False
		if diff.get(("_", "is_online")):
			if diff[("_", "is_online")][1] == "1":
				went_online = True
			else:
				went_offline = True
		
		if went_online:
			self.on_online()
		elif went_offline:
			self.on_offline()
	
	def on_online(self):
		self.state["goodnight_at"] = None
		
		last_online = self.timeline.get_last_online(time.time())
		# is new session or just break end
		is_new_sess = (time.time() - SESS_MAX_BREAK) > (last_online or 0)
		
		if not is_new_sess:
			for chat_id, chat_state in self.state["chats"].items():
				msg_to_del = chat_state.get("sess_end_msg_id")
				if msg_to_del:
					util.delete_tg_msg(chat_id, msg_to_del)
			return
		
		self.gen_new_moniker()
		
		if last_online:
			offline_duraion = format_time(int(time.time()) - last_online)
		else:
			offline_duraion = "довгого"
		
		sess_start_msg = f"🟢 <b>{self.name}</b> тепер " \
			f"<i>{self.moniker}</i>" \
			f" після {offline_duraion} відпочинку\n"
		sess_start_msg += f"<i>{get_wish()}</i>"
		
		for chat_id, chat_state in self.state["chats"].items():
			msg_id = self.notify_chat(
				chat_id, sess_start_msg, as_html=True)
			chat_state["sess_end_msg_id"] = None
	
	def on_offline(self):
		hour_local = (time.gmtime().tm_hour + util.get_hours_offset()) % 24
		if hour_local > 23 or hour_local < 6:
			self.state["goodnight_at"] = int(time.time()) + (60 * 15)
		
		sess_end = int(time.time())
		sess_start = self.timeline.get_sess_start(sess_end)
		if sess_start == None:
			return
		sess = self.timeline.get_segment(sess_start, sess_end)
		
		sess_end_msg = ""
		sess_end_msg += f"🔴 <b>{self.name}</b> більше не " \
			f"<i>{self.moniker}</i> :(\n"
		sess_end_msg += f"<pre>{sess.format(easter300=True)}</pre>"
		
		for chat_id, chat_state in self.state["chats"].items():
			msg_id = self.notify_chat(chat_id, sess_end_msg,
				as_html=True, silent=True)
			chat_state["sess_end_msg_id"] = msg_id
	
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
			

class PlayerTimeline():
	def __init__(self, player_uid):
		self.player_uid = player_uid
		self.timeline_path = TIMELINE_DIR / f"{player_uid}.txt"
		self.cur_stats = {} # keys are tuples (legend or "_", stat_name)
		
		TIMELINE_DIR.mkdir(exist_ok=True)
		self.timeline_handle = self.timeline_path.open("a", encoding="utf-8")
		self.fill_cur_stats()
	
	def fill_cur_stats(self):
		self.cur_stats = {}
		
		if not self.timeline_path.exists():
			return
		
		for entry in self.iter():
			self.cur_stats[(entry.legend, entry.stat_name)] = entry.stat_value
	
	def add_entry(self, entry, flush=True):
		self.cur_stats[(entry.legend, entry.stat_name)] = str(entry.stat_value)
		self.timeline_handle.write(entry.serialize() + "\n")
		
		if flush:
			self.timeline_handle.flush()
	
	def iter(self, reverse=False):
		if reverse:
			iterable = util.reverse_readline(self.timeline_path)
		else:
			iterable = self.timeline_path.open("r")
		
		try:
			for line in iterable:
				try:
					entry = TimelineEntry.parse(line)
				except TimelineEntryError:
					if line.strip(): # do not report empty lines
						log(f"Skipping invalid entry in" \
							f" {self.player_uid}.txt timeline: '{line}'")
					continue
				
				yield entry
		except GeneratorExit:
			iterable.close()
	
	def get_segment(self, start, end):
		start_stat = {}
		entries = []
		
		for entry in self.iter():
			if entry.timestamp < start:
				start_stat[(entry.legend, entry.stat_name)] = entry.stat_value
			elif entry.timestamp > end:
				break
			else:
				entries.append(entry)
		
		return TimelineSegment(start, end, start_stat, entries)
	
	def consume_als_stat(self, player_stat):
		#timestamp = int(datetime.datetime.utcnow().timestamp())
		timestamp = int(time.time())
		diff_data = {}
		
		def _add(stat_name, stat_value, legend="_"):
			prev_value = self.cur_stats.get((legend, stat_name))
			new_value = str(stat_value)
			if prev_value == new_value:
				return False
			
			entry = TimelineEntry(timestamp, legend, stat_name, stat_value)
			self.add_entry(entry, False)
			diff_data[(legend, stat_name)] = (prev_value, new_value)
			return True
		
		_global = player_stat["global"]
		_realtime = player_stat["realtime"]
		
		_add("level",  _global["level"] + \
			_global["toNextLevelPercent"] / 100)
		
		# weird complicated logic due to strange api responses sometimes
		is_online = bool(
			_realtime["isOnline"] and (
				_realtime["currentState"] != "offline" or \
				_realtime["currentStateSinceTimestamp"] != -1
			)
		)
		_add("is_online", int(is_online))
		_add("is_banned", int(_global["bans"]["isActive"]))
		
		# a bit of logic to handle state_since deviation
		state_changed = _add("cur_state", _realtime["currentState"])
		state_since = _realtime["currentStateSinceTimestamp"]
		prev_state_since = self.cur_stats.get(("_", "state_since"), 0)
		state_since_delta = abs(int(prev_state_since) - state_since)
		if state_changed or (state_since_delta > 20):
			_add("state_since", state_since)
		
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
		
		untouched_trackers = self.get_stored_legend_trackers(selected_legend)
		for tracker in player_stat["legends"]["selected"]["data"]:
			_add("tracker_" + tracker["key"],
				tracker["value"], selected_legend)
			
			if tracker["key"] in untouched_trackers:
				untouched_trackers.remove(tracker["key"])
		
		# nullifying unavailable trackers (probably unequipped)
		# $null is treated as a special value
		for tracker_name in untouched_trackers:
			_add(f"tracker_{tracker_name}", "$null", selected_legend)
		
		self.timeline_handle.flush()
		return diff_data
	
	def get_stored_legend_trackers(self, targ_legend):
		legend_trackers = []
		for (legend, stat_name) in self.cur_stats:
			if legend != targ_legend:
				continue
			if not stat_name.startswith("tracker_"):
				continue
			legend_trackers.append(stat_name[8:])
		return legend_trackers
	
	def get_last_online(self, before_moment):
		for entry in self.iter(reverse=True):
			if entry.timestamp > before_moment:
				continue
			if entry.stat_name == "is_online" and entry.stat_value == "0":
				return entry.timestamp
	
	def get_sess_start(self, before_moment):
		sess_start = None
		for entry in self.iter(reverse=True):
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
				elif entry.stat_name == "is_online" and entry.stat_value == "0":
					sess_start = None
		
		return sess_start
	
	def close(self):
		self.timeline_handle.close()
	
	def __del__(self):
		self.close()

class TimelineSegment():
	def __init__(self, start, end, start_stat, entries):
		self.start = start
		self.end = end
		self.duration = end - start
		self.start_stat = start_stat
		self.entries = entries
		self.fill_diff()
		self.fill_end_stat()
	
	def fill_diff(self):
		self.diff = {}
		# (legend or "_", stat): (start_value, end_value)
		
		for key in self.start_stat:
			if self.start_stat[key] == "$null":
				continue
			self.diff[key] = (self.start_stat[key], self.start_stat[key])
		
		for entry in self.entries:
			key = (entry.legend, entry.stat_name)
			
			if not self.diff.get(key):
				self.diff[key] = (entry.stat_value, entry.stat_value)
				continue
			
			if entry.isnull:
				continue
			
			self.diff[key] = (self.diff[key][0], entry.stat_value)
		
		# filtering out equal start-end values
		self.diff = {k: v for k, v in self.diff.items() if v[0] != v[1]}
	
	def fill_end_stat(self):
		self.end_stat = self.start_stat.copy()
		# (legend or "_", stat): (start_value, end_value)
		
		for entry in self.entries:
			key = (entry.legend, entry.stat_name)
			self.end_stat[key] = entry.stat_value
	
	def iter_stat_stamps(self):
		stat_stamp = self.start_stat.copy()
		
		prev_timestamp = self.start
		for i, entry in enumerate(self.entries):
			if entry.timestamp != prev_timestamp:
				yield (prev_timestamp, stat_stamp)
			
			stat_stamp[(entry.legend, entry.stat_name)] = entry.stat_value
			prev_timestamp = entry.timestamp
		
		yield (prev_timestamp, stat_stamp)
	
	def format(self, easter300=False):
		legends = {}
		
		# filling matches count to display
		matches = self.get_matches()
		for match in matches:
			legend = match.get("legend")
			if not legend:
				continue
			if not legends.get(legend):
				legends[legend] = {"_matches": 0}
			legends[legend]["_matches"] += 1
		
		# filling all the trackers to display
		for legend, stat_name in self.diff:
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
			
			val_before = util.to_num(self.diff[(legend, stat_name)][0])
			val_after  = util.to_num(self.diff[(legend, stat_name)][1])
			if None in (val_before, val_after):
				stat_diff = "???"
			else:
				stat_diff = val_after - val_before
			legends[legend][stat_name[8:]] = stat_diff
		
		text = ""
		text += f"Зіграно часу: {format_time(self.duration)}\n"
		if matches:
			text += f"Зіграно матчів: {len(matches)}\n"
		
		lvl_diff = self.diff.get(("_", "level"))
		if lvl_diff:
			text += f"Левел: {lvl_diff[0]} → {lvl_diff[1]}\n"
		
		if self.diff.get(("_", "br_rank_score")):
			before = PlayerRank.from_stat(self.start_stat, mode="br")
			after  = PlayerRank.from_stat(self.end_stat,   mode="br")
			if before and after:
				text += f"Ранг в БР: {before.format()} " \
					f"→ {after.format()}\n"
		
		if self.diff.get(("_", "ar_rank_score")):
			before = PlayerRank.from_stat(self.start_stat, mode="ar")
			after  = PlayerRank.from_stat(self.end_stat,   mode="ar")
			if before and after:
				text += f"Ранг в Аренах: {before.format()} " \
					f"→ {after.format()}\n"
		
		for legend, trackers in legends.items():
			text += f"На {trans('on_'+legend)}:\n"
			for tracker, tracker_diff in trackers.items():
				text += f"  {trans(tracker)}: {tracker_diff}"
				
				if easter300 and str(tracker_diff).endswith("300"):
					text += "  </pre><span class='tg-spoiler'>" \
						"ВІДСОСИ У КРАБЕРИСТА</span><pre>"
				else:
					text += "\n"
		
		return text.strip()
	
	def get_matches(self):
		matches = []
		
		cur_state = None
		for timestamp, stat_stamp in self.iter_stat_stamps():
			new_state = stat_stamp.get(("_", "cur_state"))
			
			# if match beginning and stat changing happens at the same time
			# stat changes should be saved to the previous match
			if matches:
				if cur_state == "inMatch":
					matches[-1]["legend"] = stat_stamp.get(("_", "legend"))
				# save match stats here
			
			if new_state != cur_state:
				if new_state == "inMatch":
					matches.append({
						"start": stat_stamp.get(("_", "state_since")),
						"legend": stat_stamp.get(("_", "legend"))
					})
				elif cur_state == "inMatch":
					matches[-1]["end"] = stat_stamp.get(("_", "state_since"))
			
			cur_state = new_state
		
		return matches

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
			raise TimelineEntryError
		
		entry_split[0] = util.to_num(entry_split[0])
		entry_split[1] = util.semiurldecode(str(entry_split[1]))
		entry_split[2] = util.semiurldecode(str(entry_split[2]))
		entry_split[3] = util.semiurldecode(str(entry_split[3]))
		
		if entry_split[0] == None:
			raise TimelineEntryError
		
		return cls(*entry_split)
	
	def serialize(self):
		return " ".join((
			str(self.timestamp),
			util.semiurlencode(str(self.legend)),
			util.semiurlencode(str(self.stat_name)),
			util.semiurlencode(str(self.stat_value))
		))

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
	
	return f"<b>{mode_name}</b> зараз на карті <b>{cur_map}</b>\n<i>Через " \
	f"{cur_map_time} перейде на <b>{next_map}</b>, де буде {next_map_time}</i>"

def format_map_rotation():
	maps = alsapi.get_map_rotation()
	delim = "\n--- --- ---\n"
	
	return delim.join((
		format_map("БР",           maps["battle_royale"]),
		format_map("Ранкед БР",    maps["ranked"]),
		format_map("Арени",        maps["arenas"]),
		format_map("Ранкед арени", maps["arenasRanked"])
	))