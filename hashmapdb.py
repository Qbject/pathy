import json
import util
from pathlib import Path
from hashlib import md5
from threading import Lock
from const import *

class HashMapDb():
	def __init__(self, storage_path):
		self.storage_path = storage_path
		self.lock = Lock()
	
	def add(self, key, value):
		self.storage_path.mkdir(parents=True, exist_ok=True)
		value = util.type2bytes(value)
		file_path = self.get_key_path(key)
		
		with self.lock:
			file_path.write_bytes(value)
	
	def get(self, key, data_type=bytes):
		file_path = self.get_key_path(key)
		if not file_path.exists():
			return None
		
		with self.lock:
			content = file_path.read_bytes()
		
		return util.bytes2type(content, data_type)
	
	def delete(self, key):
		file_path = self.get_key_path(key)
		file_path.unlink()
	
	def get_key_path(self, key):
		filename = md5(str(key).encode("utf-8")).hexdigest()
		return self.storage_path / filename

singleton = HashMapDb(HASHMAPDB_DIR)