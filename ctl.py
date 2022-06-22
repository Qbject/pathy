import time, traceback, sys, subprocess, json
import util
from pathlib import Path
from hashlib import md5
from multiprocessing.connection import Client
from util import log
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
		
		elif action == "get_web_endpoint":
			action = args.get("action", "")
			key = md5((WEBAPI_SECRET + action).encode("utf-8")).hexdigest()
			return f"{key}/{action}"
		
		elif action == "processes":
			return subprocess.check_output(["ps", "aux"],
				stderr=subprocess.STDOUT, text=True)
		
		elif action == "start":
			start()
			return
		
		elif action == "stop":
			stop()
			return
		
		elif action == "status":
			ensure_running()
			return send("status")
		
		elif action == "tgupdate":
			handle_tg_upd(body_raw)
			return
		
		elif action == "setdelay":
			ensure_running()
			send("setdelay", delay=args.get("delay", 1))
			return
		
		elif action == "matches":
			ensure_running()
			send("matches", uid=args.get("uid", "1007161381428"))
			return
		
		else:
			raise ValueError(f"Unknown Pathy ctl action: {action}")
		
	except Exception:
		err_msg = f"Failed to execute action {action}:" \
		f"\n{traceback.format_exc()}"
		log(err_msg, err=True, send_tg=True)
		return "Failed to handle request"

def start():
	pathy_dir = Path(__file__).parent
	daemon_file = pathy_dir / "daemon.py"
	subprocess.Popen(["python3", daemon_file, "start"])
	
	for _ in range(10):
		time.sleep(0.5)
		if is_alive():
			return
	
	raise OSError("Daemon process started, but not responding")

def stop():
	send("stop")

def send(msg, **args):
	conn = Client(DAEMON_ADDR, authkey=DAEMON_AUTHKEY)
	conn.send((msg, args))
	
	if not conn.poll(5):
		try:
			conn.send("timeout, closing")
		except Exception:
			pass
		raise TimeoutError(
			f"Ctl: no response to msg {msg}")
	resp = conn.recv()
	conn.close()
	return resp

def ensure_running():
	if is_alive():
		return True
	
	downtime = get_downtime()
	
	try:
		start()
	except Exception as e:
		log(f"Detected daemon down for {downtime:.2f}s, " \
			f"failed to restart:\n{traceback.format_exc()}",
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

def get_last_state_save():
	if not DAEMON_STATE.exists():
		return None
	
	state_raw = DAEMON_STATE.read_text(encoding="utf-8")
	state = json.loads(state_raw)
	return state.get("last_save") or None

def get_downtime():
	return time.time() - (get_last_state_save() or 0.0)

def handle_tg_upd(body_raw):
	update = util.TgUpdate.from_raw_body(body_raw)
	
	if not update.is_msg():
		return
	if not update.is_whitelisted():
		_tab = "\t"
		log(f"Msg from not whitelisted chat:\n" \
			f"{json.dumps(update.data, indent=_tab)}", send_tg=True)
		return
	
	debug_cmd, debug_cmd_args = update.parse_debug_cmd()
	if debug_cmd:
		cmd_resp = entry(debug_cmd, debug_cmd_args) or "<empty>"
		update.reply(util.html_sanitize(cmd_resp), as_html=True)
		return
	
	bot_cmd, bot_cmd_args = update.parse_bot_command()
	if bot_cmd == "/alive":
		try:
			result = send("status")
		except ConnectionRefusedError:
			result = "😵"
		update.reply(util.html_sanitize(result), as_html=True)
		return
	
	ensure_running()
	send("tgupd", upd_body=body_raw)