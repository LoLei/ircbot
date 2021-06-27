import os
from typing import Dict

CONFIG: Dict[str, str] = dict()

CONFIG['server'] = os.environ.get("SERVER", "")
CONFIG['channel'] = os.environ.get("CHANNEL", "")
CONFIG['bot_nick'] = os.environ.get("BOT_NICK", "")
CONFIG['password'] = os.environ.get("PASSWORD", "")
CONFIG['admin_name'] = os.environ.get("ADMIN_NAME", "")
CONFIG['exit_code'] = os.environ.get("EXIT_CODE", "")
CONFIG['command_prefix'] = os.environ.get("COMMAND_PREFIX", "")
CONFIG['user_db_message_log_size'] = os.environ.get("USER_DB_MESSAGE_LOG_SIZE", "1000")
CONFIG['stopwords'] = os.environ.get("STOPWORDS", "")
CONFIG['imgur_client_id'] = os.environ.get("IMGUR_CLIENT_ID", "")
CONFIG['imgur_client_secret'] = os.environ.get("IMGUR_CLIENT_SECRET", "")

if "CI" not in os.environ:
    empties = [v[0] for v in CONFIG.items() if v[1] == ""]
    if empties:
        raise EnvironmentError(f"Unset environment variables: {empties}")
