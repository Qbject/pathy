import time, traceback
from pathlib import Path
from multiprocessing.connection import Listener

def entry(path, args, body_raw):
	pass

def exec():
	try:
		address = ('localhost', 6914) # some random port, hopefully not used by smth else
		listener = Listener(address, authkey=b'***REMOVED***')

		log("starting")
		running = True
		while running:
			conn = listener.accept()
			while True:
				msg = conn.recv()
				log(f"msg: {msg}")
				conn.send(f"echo: {msg}")

				if msg == "stop":
					running = False

				conn.close()
				break

		listener.close()
		log("stopping")
	except BaseException as e:
		log(f"Critical error:\n{traceback.format_exc()}")
		raise e


def log(text):
	log_entry = "{}: {}".format(time.asctime(), text)
	log_entry = log_entry.replace("\n", "\n\t")

	logfile = open(Path(__file__).parent / "daemon_log.txt", "a", encoding="utf-8")

	try:
		logfile.write(log_entry + "\n")
		logfile.close()
	except OSError:
		print("Failed to write to logfile: \n{}".format(traceback.format_exc()))

if __name__ == "__main__":
	exec()