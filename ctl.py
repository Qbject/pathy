import time, traceback, sys, subprocess, util, json
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
		
		else:
			ensure_running()
			return send(action, args)
		
	except Exception:
		err_msg = f"Failed to execute action {action}:" \
		f"\n{traceback.format_exc()}"
		log(err_msg, err=True)
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

def send(msg, args={}):
	conn = Client(DAEMON_ADDR, authkey=DAEMON_AUTHKEY)
	conn.send((msg, args))
	
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
		log(
			f"Detected daemon down for {downtime:.2f}s, " \
			f"failed to restart:\n{traceback.format_exc()}",
			err=True, send_tg=True)
		raise e
	
	log(
		f"Detected daemon down for {downtime:.2f}s, " \
		f"restarted successfully",
		send_tg=True)

def is_alive():
	try:
		daemon_status = send("status")
		return True
	except ConnectionRefusedError:
		return False

def get_last_sync():
	if not DAEMON_STATE.exists():
		return None
	
	state_raw = DAEMON_STATE.read_text(encoding="utf-8")
	state = json.loads(state_raw)
	return state.get("last_sync") or None

def get_downtime():
	return time.time() - (get_last_sync() or 0.0)