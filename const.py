from pathlib import Path

#TODO: move sensitive data to env
PATHY_DIR = Path(__file__).parent
CACHE_DIR = PATHY_DIR / "data/cache"
LOGS_DIR = PATHY_DIR / "data/logs"
ERROR_LOG = LOGS_DIR / "error.log"
INFO_LOG = LOGS_DIR / "info.log"

DAEMON_ADDR = ("localhost", 6914)
DAEMON_AUTHKEY = b"***REMOVED***"

DAEMON_STATE = PATHY_DIR / "data/state.json"
LOCKFILE = PATHY_DIR / "data/parent.lock"

DEBUG_CHAT_ID = ***REMOVED***

BOT_TOKEN = "***REMOVED***"
BOT_USERNAME = "***REMOVED***"

WEBAPI_SECRET = "***REMOVED***"

ASL_CHAT_ID = ***REMOVED***
DEBUG_CHAT_ID = ***REMOVED***
DL_PROXY_CHAT_ID = ***REMOVED***

MOZAM_API_KEY = "***REMOVED***"