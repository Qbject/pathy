import signal
from pathylib import PathyDaemon

def _sigterm(*_):
	raise KeyboardInterrupt

if __name__ == "__main__":
	signal.signal(signal.SIGTERM, _sigterm)
	daemon = PathyDaemon()
	try:
		daemon.start()
	except KeyboardInterrupt:
		daemon.stop()