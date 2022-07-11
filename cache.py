import json
from pathlib import Path
from hashlib import md5
from threading import Lock
from const import *

_file_id_lock = Lock()
def add_file_id(key, file_id):
	with _file_id_lock:
		CACHE_DIR.mkdir(exist_ok=True)
		
		cache = {}
		if FILE_IDS_CACHE.exists():
			cache = json.loads(FILE_IDS_CACHE.read_text(encoding="utf-8"))
		
		cache[key] = file_id
		serialized = json.dumps(cache, indent="\t")
		FILE_IDS_CACHE.write_text(serialized, encoding="utf-8")

def get_file_id(key):
	with _file_id_lock:
		if not FILE_IDS_CACHE.exists():
			return None
		
		cache = json.loads(FILE_IDS_CACHE.read_text(encoding="utf-8"))
		return cache.get(key)

_file_lock = Lock()
def add_file(key, content):
	assert isinstance(content, bytes)
	file_path = _get_file_path_by_key(key)
	
	with _file_lock:
		CACHE_DIR.mkdir(exist_ok=True)
		FILE_CACHE_DIR.mkdir(exist_ok=True)
		file_path.write_bytes(content)

def get_file(key):
	file_path = _get_file_path_by_key(key)
	if not file_path.exists():
		return None
	
	with _file_lock:
		return file_path.read_bytes()

def _get_file_path_by_key(key):
	cached_name = md5(str(key).encode("utf-8")).hexdigest()
	return FILE_CACHE_DIR / cached_name
	