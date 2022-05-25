import time, traceback, subprocess, os
from pathlib import Path

def log(text, err=False):
	log_entry = "{}: {}".format(time.asctime(), text)
	log_entry = log_entry.replace("\n", "\n\t")
	
	logs_dir = Path(__file__).parent / "data/logs"
	logs_dir.mkdir(exist_ok=True)
	
	if err:
		logfile = open(logs_dir / "error.log", "a", encoding="utf-8")
	else:
		logfile = open(logs_dir / "info.log", "a", encoding="utf-8")
	
	try:
		logfile.write(log_entry + "\n")
		logfile.close()
	except Exception:
		print("Failed to write to logfile: \n{}".format(traceback.format_exc()))

def git_pull():
	pathy_dir = Path(__file__).parent
	os.chdir(pathy_dir)
	process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
	output = process.communicate()[0]
	return output