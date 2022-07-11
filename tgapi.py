import requests, json, re
import util, cache
from pathlib import Path
from const import *

class TgBotApiError(Exception):
	pass

def call(method, params={}, files={}):
	resp = requests.post(
		f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
		data=params,
		files=files
	)
	tg_reply = json.loads(resp.text)
	
	if (not "result" in tg_reply) or (not tg_reply["ok"]) or (not resp.ok):
		raise TgBotApiError("result['ok'] == False:\n" \
			+ json.dumps(tg_reply, indent="\t"))
	
	return tg_reply["result"]

def delete_msg(chat_id, msg_id):
	try:
		deleted_resp = call("deleteMessage", {
			"chat_id": chat_id,
			"message_id": msg_id
		})
		return True
	except TgBotApiError:
		util.log(f"Failed to delete msg {chat_id}/{msg_id}",
			err=True, send_tg=True)
		return False

def download_url_proxied(url, dest=None, use_cache=True):
	file_bytes = cache.get_file(f"url:{url}")
	if not use_cache or not file_bytes:
		sent_msg = send_message(DL_PROXY_CHAT_ID,
			f"Caching {url}", file_url=url)
		file_id = sent_msg["document"]["file_id"]
		
		tg_file = call("getFile", {"file_id": file_id})
		tg_url = f"https://api.telegram.org/file/bot" \
			f"{BOT_TOKEN}/{tg_file['file_path']}"
		
		resp = requests.get(tg_url, allow_redirects=True)
		file_bytes = resp.content
		
		if use_cache:
			cache.add_file(f"url:{url}", file_bytes)
	
	if not dest:
		return file_bytes
	Path(dest).write_bytes(file_bytes)

def send_message(chat_id, text, as_html=False, file_path=None, file_id=None,
		file_url=None, file_type="document", use_cache=True, **params):
	
	if len([p for p in [file_path, file_id, file_url] if p]) > 1:
		raise ValueError("Only one of file_path, file_id, "
			"file_url can be specified at the same time")
	
	if use_cache and any([file_path, file_url]):
		key = str(Path(file_path).resolve()) if file_path else file_url
		file_id = cache.get_file_id(key)
		if file_id:
			file_path = file_url = None
	
	params["chat_id"] = int(chat_id)
	params["parse_mode"] = "HTML" if as_html else None
	
	if any([file_path, file_id, file_url]):
		method = f"send{util.ucfirst(file_type)}"
		params[file_type.lower()] = file_id or file_url or "attach://file"
		params["caption"] = text
	else:
		method = "sendMessage"
		params["text"] = text
	
	if file_path:
		with open(file_path, "rb") as file:
			sent_msg = call(method, params, files={"file": file})
	else:
		sent_msg = call(method, params)
	
	if use_cache and any([file_path, file_url]):
		file_id = _get_msg_file_id(sent_msg)
		if file_id:
			cache.add_file_id(key, file_id)
	
	return sent_msg

def _get_msg_file_id(msg):
	file_props = ("animation", "audio", "document", "photo", "sticker",
		"video", "video_note", "voice")
	
	for prop in file_props:
		attachment = msg.get(prop)
		if not attachment:
			continue
		if isinstance(attachment, list):
			attachment = attachment[-1] # for multiple PhotoSizes
		return attachment.get("file_id")


class Update():
	def __init__(self, update_data):
		self.data = update_data
		self.chat_id = None
		self.from_id = None
		self.msg_id = None
		self.text = None
		self.reply_to = None
		
		if self.is_msg():
			self.chat_id = self.data["message"]["chat"]["id"]
			self.from_id = self.data["message"]["from"]["id"]
			self.msg_id = self.data["message"]["message_id"]
			self.text = self.data["message"].get("text") or \
				self.data["message"].get("caption")
			self.reply_to = self.data["message"].get("reply_to_message")
	
	@classmethod
	def from_raw_body(cls, body_raw):
		update_data = json.loads(body_raw.decode("utf-8"))
		return cls(update_data)
	
	def is_msg(self):
		return "message" in self.data
	
	def is_text_msg(self):
		if not self.is_msg():
			return False
		return "text" in self.data["message"]
	
	def reply(self, text, as_html=False, **kwargs):
		return send_message(self.chat_id, text, as_html=as_html, **kwargs)
	
	def reply_img(self, img_path, caption, as_html=False, **kwargs):
		return send_message(self.chat_id, caption, as_html=as_html,
			file_path=img_path, file_type="photo", **kwargs)
	
	def reply_vid(self, vid_path, caption, as_html=False, **kwargs):
		return send_message(self.chat_id, caption, as_html=as_html,
			file_path=vid_path, file_type="video", **kwargs)
	
	def reply_anim(self, anim_path, caption, as_html=False, **kwargs):
		return send_message(self.chat_id, caption, as_html=as_html,
			file_path=anim_path, file_type="animation", **kwargs)
	
	def is_debug_cmd(self):
		if not self.is_text_msg():
			return False
		return self.chat_id == DEBUG_CHAT_ID and \
		self.text.startswith("ctl ")
	
	def parse_debug_cmd(self):
		if not self.is_debug_cmd():
			return (None, None)
		
		cmd_arr = self.text.split(" ")
		cmd = cmd_arr[1]
		args_raw = " ".join(cmd_arr[2:])
		if args_raw:
			args = json.loads(args_raw)
		else:
			args = {}
		
		return (cmd, args)
	
	def parse_bot_command(self):
		if not self.is_text_msg():
			return (None, None)
		msg_text = self.text
		command_search = re.findall(
			"^(/[a-zA-Z0-9_]+)(@[a-zA-Z0-9_]+){0,1}", msg_text)
		if not command_search:
			return (None, None)
		
		command = command_search[0][0]
		botmention = command_search[0][1]
		if botmention and (botmention.lower() != f"@{BOT_USERNAME.lower()}"):
			return (None, None)
		
		full_command_len = len(command) + len(botmention)
		params = msg_text[full_command_len:].strip()
		
		return (command, params)
	
	def get_chat_title(self):
		if not self.is_text_msg():
			return None
		chat = self.data["message"]["chat"]
		return chat.get("title") or \
			f"{chat.get('first_name', '')} {chat.get('last_name', '')}"
	
	def format(self, as_html=False):
		_json = json.dumps(self.data, indent="\t")
		if as_html:
			resp = f"<pre>{util.sanitize_html(_json)}</pre>"
		else:
			resp = _json
		return resp