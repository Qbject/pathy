from os import getenv, environ
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def _parse_list(env_value):
	if env_value:
		return env_value.split(",")
	return []

def _parse_yt_channels(env_value):
	entries = _parse_list(env_value)
	channels = []
	
	for entry in entries:
		channel_data = {}
		channels.append(channel_data)
		channel_data["id"] = entry.split(":")[0]
		channel_data["name"] = entry.split(":")[1]
	
	return channels

ROOT_DIR     = Path(getenv("PATHY_ROOT_DIR")     or Path(__file__).parent)
TIMELINE_DIR = Path(getenv("PATHY_TIMELINE_DIR") or ROOT_DIR / "data/timeline")
LOGS_DIR     = Path(getenv("PATHY_LOGS_DIR")     or ROOT_DIR / "data/logs")
ERROR_LOG    = Path(getenv("PATHY_ERROR_LOG")    or LOGS_DIR / "error.log")
INFO_LOG     = Path(getenv("PATHY_INFO_LOG")     or LOGS_DIR / "info.log")

DAEMON_STATE      = Path(getenv("PATHY_DAEMON_STATE")      or ROOT_DIR / "data/state.json")
DAEMON_STATE_COPY = Path(getenv("PATHY_DAEMON_STATE_COPY") or ROOT_DIR / "data/state.copy.json")
DAEMON_LOCKFILE   = Path(getenv("PATHY_DAEMON_LOCKFILE")   or ROOT_DIR / "data/parent.lock")

HASHMAPDB_DIR = Path(getenv("PATHY_HASHMAPDB_DIR") or ROOT_DIR / "data/hashmapdb")

DAEMON_PORT = int(getenv("PATHY_DAEMON_PORT", 6914))
DAEMON_ADDR = ("localhost", DAEMON_PORT)
DAEMON_AUTHKEY = bytes(environ["PATHY_DAEMON_AUTHKEY"], encoding="utf-8")

BOT_TOKEN    = environ["PATHY_BOT_TOKEN"]
BOT_USERNAME = environ["PATHY_BOT_USERNAME"]

WEBAPI_SECRET = environ["PATHY_WEBAPI_SECRET"]
MOZAM_API_KEY = environ["PATHY_MOZAM_API_KEY"]

DEBUG_CHAT_ID    = int(environ["PATHY_DEBUG_CHAT_ID"])
ASL_CHAT_ID      = int(environ["PATHY_ASL_CHAT_ID"])
DL_PROXY_CHAT_ID = int(environ["PATHY_DL_PROXY_CHAT_ID"])

SESS_MAX_BREAK = int(getenv("PATHY_SESS_MAX_BREAK", 30 * 60)) # default 30 min
MAINTAINANCE_MODE = bool(int(getenv("PATHY_MAINTAINANCE_MODE", 0)))

GDRIVE_ASSETS_ID = environ["PATHY_GDRIVE_ASSETS_ID"]
GDRIVE_SERVICE_CRED = Path(getenv("PATHY_GDRIVE_SERVICE_CRED") or ROOT_DIR / "gdrive_service_cred.json")

OBSERVED_YT_CHANNELS_PRIMARY = _parse_yt_channels(getenv("PATHY_OBSERVED_YT_CHANNELS_PRIMARY"))
OBSERVED_YT_CHANNELS_SECONDARY = _parse_yt_channels(getenv("PATHY_OBSERVED_YT_CHANNELS_SECONDARY"))

EXTERNAL_HOST = environ["PATHY_EXTERNAL_HOST"]