import time, sys, subprocess, json
import util, tgapi
from pathlib import Path
from hashlib import md5
from multiprocessing.connection import Client
from util import log, get_err
from const import *

def check_web_action(web_action):
	key, action = web_action.split("/")
	if key != md5((WEBAPI_SECRET + action).encode("utf-8")).hexdigest():
		raise ValueError("Wrong webapi key")
	return action

def entry(action, args={}, body_raw=b"", from_web=False):
	try:
		if from_web:
			action = check_web_action(action)
		
		if action == "git_pull":
			return util.git_pull()
		
		elif action == "keepalive":
			return ensure_running()
		
		elif action == "get_action_url":
			return get_action_url(args.get("action", ""))
		
		elif action == "processes":
			return util.ps_aux()
		
		elif action == "start":
			return start()
		
		elif action == "stop":
			return stop()
		
		elif action == "tgupd":
			return handle_tg_upd(body_raw)
		
		elif action == "run_id":
			try:
				return send("run_id")
			except ConnectionRefusedError:
				return "NOT_RUNNING"
		
		else:
			ensure_running()
			resp = send(action, **args)
			if resp == "UNKNOWN_MSG":
				raise ValueError(f"Unknown Pathy daemon action: {action}")
			return resp
		
	except Exception:
		log(f"Failed to execute action {action}:\n{get_err()}",
			err=True, send_tg=True)
		return "Failed to handle action"

def start():
	daemon_file = ROOT_DIR / "daemon.py"
	subprocess.Popen(["python3", daemon_file])
	
	for _ in range(10):
		time.sleep(0.5)
		if is_alive():
			return
	
	raise OSError("Daemon process started, but not responding")

def stop():
	resp = send("stop", _timeout=20)
	time.sleep(0.5) # process need some additional time to fully terminate
	return resp

def send(msg, _timeout=5, **args):
	conn = Client(DAEMON_ADDR, authkey=DAEMON_AUTHKEY)
	conn.send((msg, args))
	
	if not conn.poll(_timeout):
		try:
			conn.send("timeout, closing")
		except Exception:
			pass
		raise TimeoutError(
			f"Ctl: no response to msg {msg}")
	resp = conn.recv()
	conn.close()
	return resp

def get_action_url(action):
	key = md5((WEBAPI_SECRET + action).encode("utf-8")).hexdigest()
	return f"https://{EXTERNAL_HOST}/pathy/{key}/{action}"

def ensure_running():
	if is_alive():
		return
	
	downtime = get_downtime()
	
	try:
		start()
	except Exception as e:
		log(f"Detected daemon down for {downtime:.2f}s, " \
			f"failed to restart:\n{get_err()}",
			err=True, send_tg=True)
		raise e
	
	log(f"Detected daemon down for {downtime:.2f}s, " \
		f"restarted successfully",
		send_tg=True)

def is_alive():
	try:
		daemon_status = send("status")
		return True
	except ConnectionRefusedError:
		return False

def get_downtime():
	last_up = util.get_state().get("last_save", 0.0)
	return time.time() - last_up

def handle_tg_upd(body_raw):
	"Handles updates that should not reach daemon"
	upd = tgapi.Update.from_raw_body(body_raw)
	
	if upd.is_msg() and util.is_chat_whitelisted(upd.chat_id):
		debug_cmd, debug_cmd_args = upd.parse_debug_cmd()
		if debug_cmd:
			cmd_resp = entry(debug_cmd, debug_cmd_args) or "(empty)"
			upd.reply(cmd_resp, as_html=True)
			return
		
		bot_cmd, bot_cmd_args = upd.parse_bot_command()
		if bot_cmd == "/alive":
			try:
				result = util.sanitize_html(send("status"))
			except ConnectionRefusedError:
				result = "😵"
			upd.reply(f"<pre>{result}</pre>", as_html=True)
			return
	
	ensure_running()
	send("tgupd", upd_body=body_raw)