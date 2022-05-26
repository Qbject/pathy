from pathlib import Path

PATHY_DIR = Path(__file__).parent
LOGS_DIR = PATHY_DIR / "data/logs"
ERROR_LOG = LOGS_DIR / "error.log"
INFO_LOG = LOGS_DIR / "info.log"

DAEMON_ADDR = ("localhost", 6914)
DAEMON_AUTHKEY = b"***REMOVED***"

DAEMON_STATE = PATHY_DIR / "data/state.json"

DEBUG_CHAT_ID = ***REMOVED***

BOT_TOKEN = "***REMOVED***"