import time, traceback, sys, subprocess, util, json
from pathlib import Path
from multiprocessing.connection import Client
from const import *

def entry(action, args={}, body_raw=b""):
	try:
		if action == "c92jx72h0xcj092jk/git_pull":
			return util.git_pull()
		elif action == "j394c02mx04nc23r4/keepalive":
			return ensure_running()
		elif action == "938ecj234jo0xj290/processes":
			return subprocess.check_output(["ps", "aux"],
				stderr=subprocess.STDOUT, text=True)
		else:
			ensure_running()
			return send(action)
		
	except Exception:
		err_msg = f"Failed to execute action {action}:\n{traceback.format_exc()}"
		util.log(err_msg, err=True)
		return "Failed to handle request"

def start():
	pathy_dir = Path(__file__).parent
	daemon_file = pathy_dir / "daemon.py"
	subprocess.Popen(["python3", daemon_file, "start"])

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
	except Exception:
		util.log(
			f"Daemon starting error:\n{traceback.format_exc()}",
			err=True)
	
	for _ in range(10):
		time.sleep(0.5)
		if is_alive():
			util.log(
				f"Detected daemon down for {downtime:.2f}s, " \
				f"restarted successfully",
				send_tg=True)
			return True
	
	util.log(
		f"Detected daemon down for {downtime:.2f}s, " \
		f"failed to restart (not responding)",
		send_tg=True)
	
	raise PathyDownError()

def is_alive():
	try:
		daemon_status = send("status")
		return True
	except ConnectionRefusedError:
		return False

class PathyDownError(OSError):
	pass

def get_last_sync():
	if not DAEMON_STATE.exists():
		return None
	
	state_raw = DAEMON_STATE.read_text(encoding="utf-8")
	state = json.loads(state_raw)
	return state.get("last_sync") or None

def get_downtime():
	return time.time() - (get_last_sync() or 0.0)