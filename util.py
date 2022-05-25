import time, traceback, subprocess, os
from pathlib import Path
from const import *

def log(text, err=False):
	log_entry = "{}: {}".format(time.asctime(), text)
	log_entry = log_entry.replace("\n", "\n\t")
	
	
	LOGS_DIR.mkdir(exist_ok=True)
	
	logfile = open(ERROR_LOG if err else INFO_LOG, "a", encoding="utf-8")
	
	try:
		logfile.write(log_entry + "\n")
		logfile.close()
	except Exception:
		print("Failed to write to logfile: \n{}".format(traceback.format_exc()))

def git_pull():
	pathy_dir = Path(__file__).parent
	os.chdir(pathy_dir)
	process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
	output = process.communicate()[0].decode("utf-8")
	return output