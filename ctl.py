import time, traceback, sys, subprocess, util
from pathlib import Path
from multiprocessing.connection import Client

def entry_request(request):
	action, args, body_raw = request

def entry_command(command):
	if command == "start":
		subprocess.Popen(["python3", __file__, "start"])
	

def send_to_daemon(msg):
	address = ("localhost", 6914)
	authkey = b"***REMOVED***"
	conn = Client(address, authkey=authkey)
	
	conn.send(msg)
	resp = conn.recv()
	conn.close()
	return resp


if __name__ == "__main__":
	if len(sys.argv) == 2 and sys.argv[1] == "start":
		entry_command(command="start")