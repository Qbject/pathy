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
	return syscmd(["git", "pull"])

def safe_file_write(file_path, data):
	attempts = 6
	interval = 0.5

	if type(data) == str:
		data = data.encode("utf-8")

	for i in range(attempts):
		try:
			with open(file_path, "wb") as file:
				file.write(data)
			break
		except Exception:
			log(f"Failed to write file {file_path} (attempt {i})", True)
			time.sleep(interval)

def syscmd(cmd):
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
	output = process.communicate()[0].decode("utf-8")
	return output