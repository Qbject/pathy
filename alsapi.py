import util, requests, time
from util import log
from const import *

def get_player_stat(player_uid):
	url = f"https://api.mozambiquehe.re/bridge?version=5&platform=PC" \
	f"&uid={player_uid}&auth={MOZAM_API_KEY}&merge=true&removeMerged=true"
	resp = requests.get(url)
	
	if resp.status_code == 429:
		time.sleep(1)
	elif (resp.status_code - (resp.status_code % 100)) != 200:
		raise AlsApiError(f"ALS API respond with code" \
			f" {resp.status_code}:\n{resp.text}")
	
	try:
		stat = resp.json()
	except Exception as e:
		raise AlsApiError(f"ALS API respond with" \
			f" invalid JSON:\n{resp.text}")
	
	return stat

def get_map_rotation():
	pass # TODO

class AlsApiError(Exception):
	pass