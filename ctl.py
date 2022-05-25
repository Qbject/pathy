import time, traceback, sys, subprocess, util
from pathlib import Path
from multiprocessing.connection import Client

def entry(action, args={}, body_raw=b""):
	try:
		if action == "c92jx72h0xcj092jk/git_pull":
			return util.git_pull()
		elif action == "j394c02mx04nc23r4/keepalive":
			return ensure_running()
		else:
			send(action)
		
	except Exception:
		err_msg = f"Failed to execute action {action}:\n{traceback.format_exc()}"
		util.log(err_msg, err=True)
		return "Failed to handle request"

def start():
	pathy_dir = Path(__file__).parent
	daemon_file = pathy_dir / "daemon.py"
	subprocess.Popen(["python3", daemon_file, "start"])

def send(msg, args={}):
	address = ("localhost", 6914)
	authkey = b"***REMOVED***"
	conn = Client(address, authkey=authkey)
	
	conn.send((msg, args))
	resp = conn.recv()
	conn.close()
	return resp

def ensure_running():
	if is_alive():
		return True
	
	util.log("Daemon down detected")
	try:
		start()
	except Exception as e:
		util.log(f"Failed to restart daemon:\n"\
			f"{traceback.format_exc()}", err=True)
		raise e
	
	for _ in range(3):
		time.sleep(1)
		if is_alive():
			util.log("Daemon restarted successfully")
			return True
	
	util.log("Daemon not responding after restart")
	raise PathyDownError()

def is_alive():
	try:
		daemon_status = send("status")
		return True
	except ConnectionRefusedError:
		return False

class PathyDownError(OSError):
	pass