import time, traceback, sys, subprocess
from pathlib import Path
from multiprocessing.connection import Client
import util

def entry_request(request):
	pass

def entry_command(command):
	if command == "start":
		subprocess.Popen(["python3", __file__, "start"])
		
	elif request:
		action, args, body_raw = request

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
		entry(command="start")