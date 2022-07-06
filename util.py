import time, traceback, subprocess, os, requests, json, pytz, datetime, random, re
import tgapi
from pathlib import Path
from const import *

def log(text, err=False, send_tg=False):
	log_entry = f"{time.asctime()}: {text}"
	log_entry = log_entry.replace("\n", "\n\t")
	
	LOGS_DIR.mkdir(exist_ok=True)
	
	logfile = open(ERROR_LOG if err else INFO_LOG, "a", encoding="utf-8")
	
	try:
		logfile.write(log_entry + "\n")
		logfile.close()
	except Exception:
		print(f"Failed to write to logfile:\n{traceback.format_exc()}")
		print("(failed to log) " + log_entry)
	
	if send_tg:
		msg_text = sanitize_html(log_entry)
		try:
			tgapi.call("sendMessage", {
				"chat_id": DEBUG_CHAT_ID,
				"text": "<pre>" + msg_text + "</pre>",
				"parse_mode": "HTML"
			})
		except Exception:
			print(f"Failed to send tg log:\n{traceback.format_exc()}")
			print("(failed to log) " + log_entry)

def git_pull():
	pathy_dir = Path(__file__).parent
	out = subprocess.check_output(["git", "pull"],
		stderr=subprocess.STDOUT,
		cwd=pathy_dir,
		text=True
	)
	return out

def write_file_with_retries(file_path, data, attempts=6, interval=0.5):
	if type(data) == str:
		data = data.encode("utf-8")
	
	for attempt in range(attempts):
		try:
			file_path.write_bytes(data)
			break
		except Exception as exc:
			log(f"Failed to write file {file_path} (attempt {attempt})",
				err=True)
			if attempt + 1 == attempts:
				raise exc
			time.sleep(interval)

def sanitize_html(text):
	text = text.replace("&", "&amp;")
	text = text.replace("<", "&lt;")
	text = text.replace(">", "&gt;")
	return text

def get_hours_offset():
	tz = pytz.timezone("Europe/Kiev")
	offset_seconds = tz.utcoffset(datetime.datetime.utcnow()).seconds
	offset_hours = offset_seconds / 60 / 60
	return int(offset_hours)

def to_num(str_num):
	result = None
	try:
		result = int(str_num)
	except (ValueError, TypeError):
		pass
	
	if result == None:
		try:
			result = float(str_num)
		except (ValueError, TypeError) as e:
			pass
	return result

# simple urlencoding-like algorythm for preventing spaces and "$" in text
def semiurlencode(text):
	return text.replace("%", "%25").replace(" ", "%20").replace("$", "%24")

def semiurldecode(text):
	return text.replace("%24", "$").replace("%20", " ").replace("%25", "%")

def get_rnd_str(length=16):
	return ''.join(random.choice(string.ascii_letters) for x in range(length))

def format_time(seconds_total, include_seconds=False):
	seconds_total = int(seconds_total)
	mins, secs = divmod(seconds_total, 60)
	hours, mins = divmod(mins, 60)
	days, hours = divmod(hours, 24)

	result_str = ""
	if days:
		result_str += f"{days}дн"
	if hours:
		result_str += f" {hours}год"
	if mins:
		result_str += f" {mins}хв"
	if secs and include_seconds:
		result_str += f" {secs}сек"
	if not result_str:
		result_str = f"{secs}сек"

	return result_str.strip()

def replace_char_map(txt, replacements):
	result_letters = []
	for char in txt:
		result_letters.append(replacements.get(char) or char)
	result_str = "".join(result_letters)
	return result_str

def chance(probability):
	return random.random() < probability

def calc_mid_percentage(targ_num, comp_nums):
	"""
	Really struggle to describe what this func does,
	so you better compile it in your head
	"""
	for i in range(len(comp_nums) - 1):
		prev_num = comp_nums[i]
		next_num = comp_nums[i+1]
		
		if prev_num <= targ_num < next_num:
			return int(((targ_num - prev_num) / (next_num - prev_num)) * 100)
	
	return -1

def get_yt_videos(channel_url):
	channel_page = requests.get(channel_url).text
	video_ids = re.findall("\"videoId\":\\s*\"([^\"]+)\"", channel_page)
	
	result_videos = []
	for vid_id in video_ids:
		vid_url = f"https://www.youtube.com/watch?v={vid_id}"
		if not vid_url in result_videos:
			result_videos.append(vid_url)
	
	return result_videos

def reverse_readline(path, buf_size=8192):
	"""
	A generator that returns the lines of a file in reverse order
	modified from from https://stackoverflow.com/a/23646049
	"""
	def _line(line):
		return line.decode("utf-8").strip("\r\n") + "\n"
	
	with open(path, "rb") as file:
		segment = None
		offset = 0
		file.seek(0, os.SEEK_END)
		file_size = remaining_size = file.tell()
		
		while remaining_size > 0:
			offset = min(file_size, offset + buf_size)
			file.seek(file_size - offset)
			buffer = file.read(min(remaining_size, buf_size))
			remaining_size -= buf_size
			lines = buffer.split(b"\n")
			
			# The first line of the buffer is probably not a complete line so
			# we'll save it and append it to the last line of the next buffer
			# we read
			if segment is not None:
				# If the previous chunk starts right from the beginning of line
				# do not concat the segment to the last line of new chunk.
				# Instead, yield the segment first
				
				if buffer[-1] != b"\n":
					lines[-1] += segment
				else:
					yield _line(segment)
			segment = lines[0]
			
			for index in range(len(lines) - 1, 0, -1):
				if lines[index]:
					yield _line(lines[index])
		
		# Don't yield None if the file was empty
		if segment is not None:
			yield _line(segment)

def get_legend_img(legend):
	default_img = ASSETS_DIR / "legend/default.jpg"
	legend_dir = ASSETS_DIR / f"legend/{legend}"
	if not (legend_dir.exists() and legend_dir.is_dir()):
		return default_img
	
	legend_imgs = list(legend_dir.iterdir())
	if not legend_imgs:
		return default_img
	
	return random.choice(legend_imgs)

def get_party_img(party_count):
	if party_count < 2:
		return None
	dirname = str(int(party_count)) if party_count < 5 else "5"
	
	party_dir = ASSETS_DIR / f"party/{dirname}"
	return random.choice(list(party_dir.iterdir()))

_interval_data = {}
def cap_freq(tag, min_interval):
	if not tag in _interval_data:
		_interval_data[tag] = time.time()
		return
	
	time_to_wait = min_interval - (time.time() - _interval_data[tag])
	if time_to_wait > 0:
		time.sleep(time_to_wait)
	_interval_data[tag] = time.time()

def get_state():
	def _try_read(path):
		try:
			state_raw = path.read_text(encoding="utf-8")
			return json.loads(state_raw)
		except (json.decoder.JSONDecodeError, FileNotFoundError):
			log(f"Failed to read {path.name}:\n{traceback.format_exc()}",
				err=True, send_tg=True)
	
	return _try_read(DAEMON_STATE) or _try_read(DAEMON_STATE_COPY) or {}

def is_chat_whitelisted(chat_id):
	whitelist = get_state().get("whitelisted_chats", [])
	return str(chat_id) in whitelist

def count_lines(file_path):
	newlines_count = 0
	for seg in iter_file_segments(file_path, "rb"):
		newlines_count += seg.count(b"\n")
	return newlines_count + 1

def iter_file_segments(file_path, *args, seg_size=8192, **kwargs):
	with file_path.open(*args, **kwargs) as file:
		while True:
			seg = file.read(seg_size)
			if not seg:
				break
			yield seg

def list_replace(lst, repl_from, repl_to):
	for i, el in enumerate(lst):
		if el == repl_from:
			lst[i] = repl_to