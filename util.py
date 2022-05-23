import time, traceback
from pathlib import Path

def log(text, is_error=False):
	log_entry = "{}: {}".format(time.asctime(), text)
	log_entry = log_entry.replace("\n", "\n\t")
	
	logs_dir = Path(__file__).parent / "pathy_logs"
	logs_dir.mkdir(exist_ok=True)
	
	if is_error:
		logfile = open(logs_dir / "error.log", "a", encoding="utf-8")
	else:
		logfile = open(logs_dir / "info.log", "a", encoding="utf-8")
	
	try:
		logfile.write(log_entry + "\n")
		logfile.close()
	except Exception:
		print("Failed to write to logfile: \n{}".format(traceback.format_exc()))