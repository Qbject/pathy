import util, requests, time
from util import log
from const import *

def get_player_stat(player_uid):
	url = f"https://api.mozambiquehe.re/bridge?version=5&platform=PC" \
	f"&uid={player_uid}&auth={MOZAM_API_KEY}&merge=true&removeMerged=true"
	resp = requests.get(url)
	
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
		util.log(f"ALS API invalid stat response:\n{resp.text}")
		raise AlsApiError(f"ALS API respond with invalid data")
	
	return stat

def get_map_rotation():
	pass # TODO

class AlsApiError(Exception):
	pass