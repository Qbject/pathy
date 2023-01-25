from os import getenv, environ
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR     = getenv("PATHY_ROOT_DIR")     or Path(__file__).parent
ASSETS_DIR   = getenv("PATHY_ASSETS_DIR")   or ROOT_DIR / "assets"
TIMELINE_DIR = getenv("PATHY_TIMELINE_DIR") or ROOT_DIR / "data/timeline"
LOGS_DIR     = getenv("PATHY_LOGS_DIR")     or ROOT_DIR / "data/logs"
ERROR_LOG    = getenv("PATHY_ERROR_LOG")    or LOGS_DIR / "error.log"
INFO_LOG     = getenv("PATHY_INFO_LOG")     or LOGS_DIR / "info.log"

DAEMON_STATE      = getenv("PATHY_DAEMON_STATE")      or ROOT_DIR / "data/state.json"
DAEMON_STATE_COPY = getenv("PATHY_DAEMON_STATE_COPY") or ROOT_DIR / "data/state.copy.json"
DAEMON_LOCKFILE   = getenv("PATHY_DAEMON_LOCKFILE")   or ROOT_DIR / "data/parent.lock"

DICT_ADJ             = getenv("PATHY_DICT_ADJ")             or ROOT_DIR / "dict/adj.txt"
DICT_NOUN_V_NAZ      = getenv("PATHY_DICT_NOUN_V_NAZ")      or ROOT_DIR / "dict/noun_v_naz.txt"
DICT_NOUN_V_ROD      = getenv("PATHY_DICT_NOUN_V_ROD")      or ROOT_DIR / "dict/noun_v_rod.txt"
DICT_NOUN_V_NAZ_PLUR = getenv("PATHY_DICT_NOUN_V_NAZ_PLUR") or ROOT_DIR / "dict/noun_v_naz_plur.txt"
DICT_NOUN_V_ROD_PLUR = getenv("PATHY_DICT_NOUN_V_ROD_PLUR") or ROOT_DIR / "dict/noun_v_rod_plur.txt"
DICT_PREFIXES        = getenv("PATHY_DICT_PREFIXES")        or ROOT_DIR / "dict/prefixes.txt"
DICT_HOKKU           = getenv("PATHY_DICT_HOKKU")           or ROOT_DIR / "dict/hokku.txt"

CACHE_DIR =      getenv("PATHY_CACHE_DIR")      or ROOT_DIR / "data/cache"
FILE_IDS_CACHE = getenv("PATHY_FILE_IDS_CACHE") or CACHE_DIR / "file_ids.json"
FILE_CACHE_DIR = getenv("PATHY_FILE_CACHE_DIR") or CACHE_DIR / "files"

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