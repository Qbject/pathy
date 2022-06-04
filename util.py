import time, traceback, subprocess, os, requests, json, pytz, datetime, random, re
import localtext
from pathlib import Path
from const import *
from localtext import trans

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
		msg_text = html_sanitize(log_entry)
		try:
			call_tg_api("sendMessage", {
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

def safe_file_write(file_path, data):
	attempts = 6
	interval = 0.5
	
	if type(data) == str:
		data = data.encode("utf-8")
	
	last_exc = None
	for i in range(attempts):
		try:
			file_path.write_bytes(data)
			last_exc = None
			break
		except Exception as exc:
			log(f"Failed to write file {file_path} (attempt {i})", True)
			last_exc = exc
			time.sleep(interval)
	
	if last_exc:
		raise last_exc

def call_tg_api(method, params={}, files={}):
	resp = requests.post(
		f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
		data=params,
		files=files
	)
	tg_reply = json.loads(resp.text)
	
	if (not "result" in tg_reply) or (not tg_reply["ok"]) or (not resp.ok):
		raise TgBotApiError("result['ok'] == False:\n" \
			+ json.dumps(tg_reply, indent="\t"))
	
	return tg_reply["result"]

class TgBotApiError(Exception):
	pass

def html_sanitize(text):
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

def parse_bot_command(msg_text):
	command_search = re.findall(
		"^(/[a-zA-Z0-9_]+)(@[a-zA-Z0-9_]+){0,1}", msg_text)
	if not command_search:
		return (None, None)
	
	command = command_search[0][0]
	botmention = command_search[0][1]
	if botmention and (botmention.lower() != f"@{BOT_USERNAME.lower()}"):
		return (None, None)
	
	full_command_len = len(command) + len(botmention)
	params = msg_text[full_command_len:].strip()
	
	return (command, params)

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

def dl_file_through_tg(url, dest):
	sent_msg = call_tg_api("sendDocument",
		{
		"chat_id": DL_PROXY_CHAT_ID,
		"document": url,
		"caption": f"Caching {url}"
		})
	file_id = sent_msg["document"]["file_id"]
	
	tg_file = call_tg_api("getFile", {"file_id": file_id})
	tg_url = f"https://api.telegram.org/file/bot" \
		f"{BOT_TOKEN}/{tg_file['file_path']}"
	
	resp = requests.get(tg_url, allow_redirects=True)
	open(dest, 'wb').write(resp.content)

def reverse_readline(filename, buf_size=8192):
	"""
	A generator that returns the lines of a file in reverse order
	from https://stackoverflow.com/a/23646049
	"""
	with open(filename) as fh:
		segment = None
		offset = 0
		fh.seek(0, os.SEEK_END)
		file_size = remaining_size = fh.tell()
		
		while remaining_size > 0:
			offset = min(file_size, offset + buf_size)
			fh.seek(file_size - offset)
			buffer = fh.read(min(remaining_size, buf_size))
			remaining_size -= buf_size
			lines = buffer.split('\n')
			
			# The first line of the buffer is probably not a complete line so
			# we'll save it and append it to the last line of the next buffer
			# we read
			if segment is not None:
				# If the previous chunk starts right from the beginning of line
				# do not concat the segment to the last line of new chunk.
				# Instead, yield the segment first
				
				if buffer[-1] != '\n':
					lines[-1] += segment
				else:
					yield segment
			segment = lines[0]
			
			for index in range(len(lines) - 1, 0, -1):
				if lines[index]:
					yield lines[index]
		
		# Don't yield None if the file was empty
		if segment is not None:
			yield segment
