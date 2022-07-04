from pathlib import Path

#TODO: move sensitive data to env
PATHY_DIR = Path(__file__).parent
ASSETS_DIR = PATHY_DIR / "assets"
CACHE_DIR = PATHY_DIR / "data/cache"
TIMELINE_DIR = PATHY_DIR / "data/timeline"
LOGS_DIR = PATHY_DIR / "data/logs"
ERROR_LOG = LOGS_DIR / "error.log"
INFO_LOG = LOGS_DIR / "info.log"

DAEMON_ADDR = ("localhost", 6914)
DAEMON_AUTHKEY = b"***REMOVED***"

DAEMON_STATE = PATHY_DIR / "data/state.json"
DAEMON_STATE_COPY = PATHY_DIR / "data/state.copy.json"
DAEMON_LOCKFILE = PATHY_DIR / "data/parent.lock"


BOT_TOKEN = "***REMOVED***"
BOT_USERNAME = "***REMOVED***"

WEBAPI_SECRET = "***REMOVED***"

DEBUG_CHAT_ID = ***REMOVED***
ASL_CHAT_ID = ***REMOVED***
DL_PROXY_CHAT_ID = ***REMOVED***

MOZAM_API_KEY = "***REMOVED***"

TEXT_GRS_DICT = PATHY_DIR / "textdata/grs.txt"
TEXT_GRS_PLUR_DICT = PATHY_DIR / "textdata/grs_plur.txt"
TEXT_ADJECTIVES_DICT = PATHY_DIR / "textdata/adjectives.txt"
TEXT_PREFIXES_DICT = PATHY_DIR / "textdata/prefixes.txt"

SESS_MAX_BREAK = 30 * 60 # 30 min