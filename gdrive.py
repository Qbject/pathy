from google.oauth2 import service_account
from googleapiclient.discovery import build
import random, requests
import tgapi
from const import *
from util import bytes2type


cred_scopes = ["https://www.googleapis.com/auth/drive.readonly"]
creds = service_account.Credentials.from_service_account_file(
	str(GDRIVE_SERVICE_CRED), scopes=cred_scopes)
service = build("drive", "v3", credentials=creds)

class GoogleDriveFile():
	def __init__(self, data, fields="*", attempts=3):
		self.data = data
		self.fields = fields
		self.attempts = attempts
		self.cached_children = {}
	
	@classmethod
	def from_id(cls, file_id):
		return cls({"id": file_id}, "id")
	
	def reload(self, fields=None):
		self.fields = fields or self.fields
		self.clear_cache()
		self.data = service.files().get(
			fileId=self.data["id"], fields=self.fields).execute()
	
	def clear_cache(self):
		self.cached_children = {}
	
	def is_dir(self):
		return self.data["mimeType"] == "application/vnd.google-apps.folder"
	
	def children(self, fields=None, use_cache=True):
		fields = fields or self.fields
		if use_cache and fields in self.cached_children:
			return self.cached_children[fields]
		
		def _list(page_token):
			params = {
				"q": f"'{self.data['id']}' in parents",
				"fields": f"nextPageToken, files({fields})"
			}
			if page_token:
				params["pageToken"] = page_token
			
			results = None
			last_err = None
			for attempt in range(self.attempts):
				try:
					results = service.files().list(**params).execute()
					break
				except Exception as e:
					last_err = e
			if results is None: raise last_err
			return (results.get("files", []), results.get("nextPageToken"))
		
		files = []
		page_token = None
		while True:
			(page_files, page_token) = _list(page_token)
			files.extend(page_files)
			if not page_token: break
		
		children = [GoogleDriveFile(file, fields=fields) for file in files]
		if use_cache: self.cached_children[fields] = children
		return children
	
	def child(self, name, fields=None):
		fields = fields or self.fields
		name = str(name)
		
		for file in self.children(fields=fields):
			if file.data["name"] == name: return file
	
	def __truediv__(self, other):
		return self.child(other)
	
	def random_child(self, fields=None):
		fields = fields or self.fields
		children = self.children(fields=fields)
		if not children: return None
		return random.choice(children)
	
	def send_tg(self, *args, force_file_type=None, **kwargs):
		file_type = tgapi.get_file_type(
			self.data["mimeType"], force_type=force_file_type)
		return tgapi.send_message(*args, **kwargs,
			file_url=self.data["webContentLink"], file_type=file_type)
	
	def read(self, data_type=bytes):
		resp = requests.get(self.data["webContentLink"])
		resp.raise_for_status()
		return bytes2type(resp.content, data_type)