import time, traceback, subprocess, os
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
		msg_text = html_sanitize(log_entry)
		try:
			call_tg_api("sendMessage", {
				"chat_id": DEBUG_CHAT_ID,
				"text": msg_text,
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

	for i in range(attempts):
		try:
			with open(file_path, "wb") as file:
				file.write(data)
			break
		except Exception:
			log(f"Failed to write file {file_path} (attempt {i})", True)
			time.sleep(interval)

def call_tg_api(method, params={}, files={}):
	resp = requests.post(
		f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
		data=params,
		files=files
	)
	tg_reply = json.loads(resp.text)
	
	if (not "result" in tg_reply) or (not tg_reply["ok"]):
		raise TgBotApiError("result['ok'] == False:\n" \
			+ json.dumps(tg_reply, indent="\t"))
	
	return tg_reply["result"]

class TgBotApiError(ValueError):
	pass

def html_sanitize(text):
	text = text.replace("&", "&amp;")
	text = text.replace("<", "&lt;")
	text = text.replace(">", "&gt;")
	return text