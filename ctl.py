import time, traceback, sys, subprocess, util
from pathlib import Path
from multiprocessing.connection import Client

def entry_request(request):
	action, args, body_raw = request

def entry_command(command):
	if command == "start":
		start_daemon()
	
def start_daemon():
	pathy_dir = Path(__file__).parent
	daemon_file = pathy_dir / "daemon.py"
	subprocess.Popen(["python3", daemon_file, "start"])

def send_to_daemon(msg):
	address = ("localhost", 6914)
	authkey = b"***REMOVED***"
	conn = Client(address, authkey=authkey)
	
	conn.send(msg)
	resp = conn.recv()
	conn.close()
	return resp

