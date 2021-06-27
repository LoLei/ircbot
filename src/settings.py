import os
from typing import Dict

CONFIG: Dict[str, str] = dict()

CONFIG['server'] = os.environ["SERVER"]
CONFIG['channel'] = os.environ["CHANNEL"]
CONFIG['bot_nick'] = os.environ["BOT_NICK"]
CONFIG['password'] = os.environ["PASSWORD"]
CONFIG['admin_name'] = os.environ["ADMIN_NAME"]
CONFIG['exit_code'] = os.environ["EXIT_CODE"]
CONFIG['command_prefix'] = os.environ["COMMAND_PREFIX"]
CONFIG['user_db_message_log_size'] = os.environ["USER_DB_MESSAGE_LOG_SIZE"]
CONFIG['stopwords'] = os.environ["STOPWORDS"]
CONFIG['imgur_client_id'] = os.environ["IMGUR_CLIENT_ID"]
CONFIG['imgur_client_secret'] = os.environ["IMGUR_CLIENT_SECRET"]
