import util, requests, time
from util import log
from const import *

def get_player_stat(player_uid):
	url = f"https://api.mozambiquehe.re/bridge?version=5&platform=PC" \
	f"&uid={player_uid}&merge=true&removeMerged=true"
	resp = requests.get(url, headers={"Authorization": MOZAM_API_KEY})
	
	if resp.status_code == 429:
		time.sleep(1)
		return get_player_stat(player_uid)
	
	if not resp.ok:
		raise AlsApiError(f"ALS API respond with code " \
			f"{resp.status_code}: {resp.reason}")
	
	try:
		stat = resp.json()
		_ = stat["global"]
		_ = stat["realtime"]
	except Exception as e:
		log(f"ALS API invalid stat response:\n{resp.text}")
		raise AlsApiError(f"ALS API respond with invalid data")
	
	return stat

def get_map_rotation():
	url = f"https://api.mozambiquehe.re/maprotation?version=5"
	resp = requests.get(url, headers={"Authorization": MOZAM_API_KEY})
	
	if resp.status_code == 429:
		time.sleep(1)
		return get_map_rotation()
	
	if not resp.ok:
		raise AlsApiError(f"ALS API respond with code " \
			f"{resp.status_code}: {resp.reason}")
	
	try:
		rotation = resp.json()
	except Exception as e:
		log(f"ALS API invalid map rotation response:\n{resp.text}")
		raise AlsApiError(f"ALS API respond with invalid data")
	
	return rotation

def get_craft_rotation():
	url = f"https://api.mozambiquehe.re/crafting"
	resp = requests.get(url, headers={"Authorization": MOZAM_API_KEY})
	
	if resp.status_code == 429:
		time.sleep(1)
		return get_craft_rotation()
	
	if not resp.ok:
		raise AlsApiError(f"ALS API respond with code " \
			f"{resp.status_code}: {resp.reason}")
	
	try:
		rotation = resp.json()
	except Exception as e:
		log(f"ALS API invalid craft rotation response:\n{resp.text}")
		raise AlsApiError(f"ALS API respond with invalid data")
	
	return rotation

class AlsApiError(Exception):
	pass