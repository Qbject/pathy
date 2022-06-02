import time, datetime
import util, localtext, alsapi
from util import log
from const import *
from localtext import trans


class TrackedPlayer():
	def __init__(self, player_state):
		self.uid = player_state["uid"]
		self.state = player_state
		self.timeline = PlayerTimeline(self.uid)
	
	def serialize(self):
		return self.state
	
	def get_name(self):
		return self.timeline.cur_stats.get(("_", "name"), "???")
	
	def get_moniker(self):
		return self.timeline.cur_stats.get(("_", "moniker"), "???")
	
	def update(self):
		stat = alsapi.get_player_stat(self.uid)
		diff = self.timeline.consume_als_stat(stat)
		
		if diff.get(("_", "is_online")) and diff[("_", "is_online")] == "0":
			sess_end = time.time()
			sess_start = self.get_session_start(sess_end)
			sess_diff = self.timeline.get_diff(sess_start, sess_end)
			
			sess_summary_msg = ""
			sess_summary_msg += f"{self.get_name()} " \
				f"більше не {self.get_moniker()} :(\n"
			
			sess_length = sess_end - sess_start
			sess_summary_msg += f"Зіграно часу: " \
				f"{util.format_time(sess_length)}\n"
			sess_summary_msg += f"Левел: {sess_diff[('_', stat_name)][0]} ->" \
				f" {sess_diff[('_', stat_name)][1]}\n"
			
			for legend, stat_name in sess_diff:
				delta = sess_diff[(legend, stat_name)][1] - \
					sess_diff[(legend, stat_name)][0]
				sess_summary_msg += f"{trans(stat_name)} на " \
					f"{trans('on_'+legend)}: {delta}\n"
			self.notify_chats(sess_summary_msg)
	
	def get_session_start(self, before_time):
		session_max_break = 30 * 60 # 30 min
		
		sess_start = None
		for time, legend, stat_name, stat_value in self.iter(reverse=True):
			if time > before_time:
				continue
			
			if sess_start == None:
				# looking for went online event
				if stat_name == "is_online" and stat_value == "1":
					sess_start = time
			else:
				# looking for any event happened earlier
				# than (sess_start - session_max_break) or to reset
				# sess_start if another went offline event found earlier
				if time < (sess_start - session_max_break):
					break
				elif stat_name == "is_online" and stat_value == "0":
					sess_start = None
		
		return sess_start
	
	def notify_chats(self, msg, as_html=False, silent=False):
		for chat_id, chat_state in self.state.chats:
			call_tg_api("sendMessage", {
				"chat_id": chat_id,
				"text": msg,
				"parse_mode": "HTML" if as_html else None,
				"disable_notification": silent
			})
			

class PlayerTimeline():
	def __init__(self, player_uid):
		self.player_uid = player_uid
		self.timeline_path = TIMELINE_DIR / f"{player_uid}.txt"
		self.cur_stats = {} # keys are tuples (legend or "_", stat_name)
		
		TIMELINE_DIR.mkdir(exist_ok=True)
		self.timeline_handle = self.timeline_path.open("a", encoding="utf-8")
		self.load()
	
	def load(self):
		self.cur_stats = {}
		
		if not self.timeline_path.exists():
			return
		
		for _, legend, stat_name, stat_value in self.iter():
			self.cur_stats[(legend, stat_name)] = stat_value
	
	def add_entry(self, timestamp, legend, stat_name, stat_value, flush=True):
		self.cur_stats[(legend, stat_name)] = str(stat_value)
		
		line = " ".join((
			str(timestamp),
			util.semiurlencode(str(legend)),
			util.semiurlencode(str(stat_name)),
			util.semiurlencode(str(stat_value))
		))
		
		self.timeline_handle.write(line + "\n")
		if flush:
			self.timeline_handle.flush()
	
	def iter(self, reverse=False):
		if reverse:
			iterable = util.reverse_readline(self.timeline_path)
		else:
			iterable = self.timeline_path.open("r")
		
		try:
			for line in iterable:
				entry = line.strip(" \r\n")
				entry_split = entry.split(" ")
				
				if not entry:
					continue
				
				def _log_invalid():
					log(f"Skipping invalid entry in" \
						f" {self.player_uid}.txt timeline: '{entry}'")
				
				if len(entry_split) != 4:
					_log_invalid()
					continue
				
				entry_split[0] = util.to_num(entry_split[0])
				entry_split[1] = util.semiurldecode(str(entry_split[1]))
				entry_split[2] = util.semiurldecode(str(entry_split[2]))
				entry_split[3] = util.semiurldecode(str(entry_split[3]))
				
				if entry_split[0] == None:
					_log_invalid()
					continue
				
				yield entry_split
		except GeneratorExit:
			iterable.close()
	
	def get_diff(self, start, end):
		diff_data = {}
		# (legend or "_", stat): (start_value, end_value)
		
		for time, legend, stat_name, stat_value in self.iter():
			if time > end:
				break
			
			key = (legend, stat_name)
			if not diff_data.get(key):
				diff_data[key] = (None, None)
			
			if time < start:
				diff_data[key][0] = stat_value
			
			elif start <= time <= end:
				if stat_value != "$null":
					if diff_data[key][0] in (None, "$null"):
						diff_data[key][0] = stat_value
					diff_data[key][1] = stat_value
		
		for key, stat_values in diff_data.items():
			if (None in stat_values) or \
			("$null" in stat_values) or \
			(stat_values[0] == stat_values[1]):
				diff_data.remove(key)
		
		return TimelineDiff(diff_data)
	
	def consume_als_stat(self, player_stat):
		timestamp = int(datetime.datetime.utcnow().timestamp())
		diff_data = {}
		
		def _add(stat_name, stat_value, legend="_"):
			prev_value = self.cur_stats.get((legend, stat_name))
			new_value = str(stat_value)
			if prev_value == new_value:
				return
			
			# this value from api may deviate
			if stat_name == "state_since":
				if abs(int(prev_value or 0) - int(new_value)) < 20:
					return
			
			self.add_entry(timestamp, legend, stat_name, stat_value, False)
			diff_data[(legend, stat_name)] = (prev_value, new_value)
		
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
		_add("cur_state", _realtime["currentState"])
		_add("state_since", _realtime["currentStateSinceTimestamp"])
		_add("is_banned", int(_global["bans"]["isActive"]))
		
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
		
		untouched_trackers = self.get_legend_trackers(selected_legend)
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
		return TimelineDiff(diff_data)
	
	def get_legend_trackers(self, targ_legend):
		legend_trackers = []
		for (legend, stat_name) in self.cur_stats:
			if legend != targ_legend:
				continue
			if not stat_name.startswith("tracker_"):
				continue
			legend_trackers.append(stat_name[8:])
		return legend_trackers
	
	def close(self):
		self.timeline_handle.close()
	
	def __del__(self):
		self.close()

class TimelineDiff():
	def __init__(self, data):
		self.data = data
