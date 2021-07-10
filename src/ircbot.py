__author__ = "Lorenz Leitner"
__version__ = "1.3.3"
__license__ = "MIT"

import collections
import json
import logging
import os
import random
import socket
import string
import threading
import time
from typing import Tuple, List, Dict, Union
from pathlib import Path

from tinydb import TinyDB, Query

from src.command import HelpCommand, CommandCommand, AboutCommand, \
    LmCommand, SentimentCommand, TimeCommand, DateCommand, \
    UptimeCommand, UpdogCommand, FrequentWordsCommand, \
    WordCloudCommand, WeekdayCommand, InterjectCommand, \
    CopypastaCommand, ShrugCommand, Command
from src.receiver.receiver import Receiver
from src.sender.sender import Sender
from src.settings import CONFIG
from src.ircmsg import IrcMsg

# Misc settings
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    level=logging.DEBUG)
BOT_PATH = os.path.dirname(os.path.abspath(__file__))


class IRCBot:
    def __init__(self) -> None:
        # Socket
        self._irc_sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_timeout = 60 * 3  # 2 min pings on snoonet

        # User defined options
        self._server: str = CONFIG['server']
        self._channel: str = CONFIG['channel']
        self._nick: str = CONFIG['bot_nick']
        self._password: str = CONFIG['password']
        self._admin_name: str = CONFIG['admin_name']
        self._exitcode: str = CONFIG['exit_code']
        self._command_prefix: str = CONFIG['command_prefix']
        self._user_db_message_log_size: int = int(CONFIG['user_db_message_log_size'])
        self._user_db: TinyDB = TinyDB(IRCBot.get_storage_dir_file('users.json'))

        # Default memvars
        self._max_user_name_length = 17  # Freenode, need to check snoonet
        self._max_message_length = 0  # Set later
        self._responses: List[str] = []
        self._bot_bros: List[str] = []
        self._triggers: Dict[str, List] = {}
        self._min_msg_interval = 1.01
        self._last_command_time = 0.0
        self._last_ping_time: float = time.time()
        self._re_files_txt_interval = 60.0 * 15
        self._repeated_message_sleep_time = 1.25
        self._user_meta = ""  # Set later
        self._replace_strings = ['ADMIN', 'USER', 'BOTNAME', 'COMMANDPREFIX']
        self._version: str = __version__
        self._join_time = 0.0
        self._join_delay = 10.0
        self._ignoring_messages = True

        # IRC message sender (and receiver) (TODO: Inject dependencies)
        self._sender = Sender(self._irc_sock, self.repeated_message_sleep_time)
        self._receiver = Receiver(self._irc_sock, self._socket_timeout)

        # Commands (must be after sender, because commands need the sender)
        self._commands: Dict[str, Command] = self.create_commands(self._sender)
        self._max_command_length = self.get_max_command_length()

        self._creation_time: float = time.time()

    @property
    def nick(self) -> str:
        return self._nick

    @property
    def command_prefix(self) -> str:
        return self._command_prefix

    @property
    def commands(self) -> Dict[str, Command]:
        return self._commands

    @property
    def repeated_message_sleep_time(self) -> float:
        return self._repeated_message_sleep_time

    @property
    def admin_name(self) -> str:
        return self._admin_name

    @property
    def version(self) -> str:
        return self._version

    @property
    def channel(self) -> str:
        return self._channel

    @property
    def user_db(self) -> TinyDB:
        return self._user_db

    @property
    def user_db_message_log_size(self) -> int:
        return self._user_db_message_log_size

    @property
    def creation_time(self) -> float:
        return self._creation_time

    @property
    def triggers(self) -> Dict[str, List]:
        return self._triggers

    @property
    def max_message_length(self) -> int:
        return self._max_message_length

    def create_commands(self, sender: Sender) -> Dict[str, Command]:
        return {
            'about': AboutCommand(self, sender),
            'cmds': CommandCommand(self, sender),
            'copypasta': CopypastaCommand(self, sender),
            'date': DateCommand(self, sender),
            'help': HelpCommand(self, sender),
            'interject': InterjectCommand(self, sender),
            'lastmessage': LmCommand(self, sender),
            'sentiment': SentimentCommand(self, sender),
            'shrug': ShrugCommand(self, sender),
            'time': TimeCommand(self, sender),
            'updog': UpdogCommand(self, sender),
            'uptime': UptimeCommand(self, sender),
            'weekday': WeekdayCommand(self, sender),
            'wordcloud': WordCloudCommand(self, sender),
            'words': FrequentWordsCommand(self, sender),
        }

    @staticmethod
    def get_storage_dir_file(filename: str) -> str:
        return str(Path(BOT_PATH).parent / 'storage' / filename)

    @staticmethod
    def get_resources_dir_file(filename: str) -> str:
        return str(Path(BOT_PATH) / 'resources' / filename)

    def _reset_socket(self) -> None:
        self._irc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sender.irc_socket = self._irc_sock
        self._receiver.irc_socket = self._irc_sock

    def connect(self, reconnect: bool = False) -> bool:
        if reconnect:
            self._reset_socket()
        try:
            self._irc_sock.connect((self._server, 6667))
        except socket.gaierror as e:
            logging.error(e)
            return False

        logging.info("socket connection established")
        self._sender.send_auth(self._nick, self._password)
        logging.info("initial IRC connection successful")
        return True

    def join(self, chan: str) -> None:
        self._sender.send_join(chan)
        self._join_time = time.time()

    def ping(self, msg: str) -> None:
        # PING code can be in a multiline message
        ping_code = msg[msg.rindex('PING') + len('PING :'):]
        self._sender.send_pong(ping_code)

    def startbatch(self, channel: str) -> str:
        batch_id = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=14))
        # Multiline not in prod yet:
        # https://github.com/ircv3/ircv3-specifications/pull/398
        batch_type = 'draft/multiline'
        self._sender.send_start_batch(channel, batch_id, batch_type)
        return batch_id

    def endbatch(self, batch_id: str) -> None:
        self._sender.send_end_batch(batch_id)

    def receive_msg(self) -> Union[str, List[str]]:
        return self._receiver.receive_msg()

    def get_max_command_length(self) -> int:
        max_length = 0
        for command_name in self.commands:
            if len(command_name) > max_length:
                max_length = len(command_name)
        return max_length

    def get_max_message_length(self) -> int:
        irc_max_msg_len = 510
        return irc_max_msg_len - (
                len(self._user_meta) +
                len("PRIVMSG ") +
                len(self.channel) +
                len(" :") +
                len("\n"))

    def get_responses(self) -> List[str]:
        with open(os.path.join(IRCBot.get_resources_dir_file('responses.txt'))) as f:
            responses = f.readlines()
        responses = [r.strip() for r in responses]
        responses = [r.replace("ADMIN", self.admin_name, 1) for r in responses]
        responses = [r.replace("COMMANDPREFIX", self.command_prefix, 1)
                     for r in responses]
        return responses

    def get_bot_bros(self) -> List[str]:
        with open(os.path.join(IRCBot.get_resources_dir_file('bots.txt'))) as f:
            bots = f.readlines()
        bots = [b.strip() for b in bots]
        return bots

    def get_triggers(self) -> Dict[str, List]:
        with open(os.path.join(IRCBot.get_resources_dir_file('triggers.json'))) as f:
            triggers = json.load(f)

        # Replace placeholders in file with variables
        replaced_triggers = triggers.copy()
        for key, _ in triggers.items():
            if set(list(key)) & set('\t'.join(self._replace_strings)):
                new_key = key.replace('ADMIN', self.admin_name.lower())
                new_key = new_key.replace('BOTNAME', self._nick.lower())
                replaced_triggers[new_key] = triggers[key]
                replaced_triggers.pop(key)
        return replaced_triggers

    def read_db_txt_files(self) -> Tuple[List[str], List[str], Dict[str, List]]:
        return self.get_responses(), self.get_bot_bros(), self.get_triggers()

    def run(self) -> None:
        self.connect()

        # Thread to re-read the database files
        t_read_database = threading.Thread(
            target=self.re_read_txt_database_loop)
        t_read_database.start()

        # Thread to continuously receive and parse messages
        t_recv_parse_msg = threading.Thread(
            target=self.receive_and_parse_msg_loop)
        t_recv_parse_msg.start()

    def re_read_txt_database_loop(self) -> None:
        while True:
            read_ins = self.read_db_txt_files()
            self._responses = read_ins[0]
            self._bot_bros = read_ins[1]
            self._triggers = read_ins[2]
            time.sleep(self._re_files_txt_interval)

    def receive_and_parse_msg_loop(self) -> None:
        t = threading.currentThread()
        while getattr(t, "do_run", True):
            self.receive_and_parse_msg()

    def receive_and_parse_msg(self) -> None:
        ircmsgs = self.receive_msg()
        for ircmsg in ircmsgs:
            self.receive_and_parse_irc_msg(ircmsg)

    def check_if_ignore_messages(self) -> bool:
        # Ignore messages the first n seconds after joining
        # Prevents duplicate parsing of backfeed messages
        if (time.time() - self._join_time) < self._join_delay:
            logging.info("Still ignoring messages")
            return True
        else:
            if self._ignoring_messages:
                logging.info(
                    f"Stopped ignoring messages after "
                    f"{self._join_delay} seconds")
            self._ignoring_messages = False
            return False

    def receive_and_parse_irc_msg(self, raw_ircmsg: str) -> None:
        if not raw_ircmsg:
            logging.info("empty raw_ircmsg possibly due to timeout/no connection")
            self.connect(reconnect=True)
            time.sleep(self._socket_timeout / 10)
            return

        if raw_ircmsg.find("PRIVMSG") != -1:
            if self.check_if_ignore_messages():
                return

            ircmsg = IrcMsg.from_raw(raw_ircmsg)
            logging.debug("Parsed IRC message:")
            logging.debug(ircmsg)

            if ircmsg is None:
                logging.warning("IRC message parsing failed, see previous log")
                return

            # Ignore PMs
            if ircmsg.channel == self.nick:
                logging.warning("Ignoring PM from: " + ircmsg.name)
                return

            # Put user in data base or update existing user
            self.handle_user_on_message(ircmsg.name, ircmsg.msg)

            if (ircmsg.name.lower() == self.admin_name.lower() and
                    ircmsg.msg.rstrip() == self._exitcode):
                self._sender.send_privmsg("cya", self.channel,
                                          self.max_message_length)
                self._sender.send_quit()
                return

            # Normal user messages/commands
            if len(ircmsg.name) < self._max_user_name_length:
                if ircmsg.name in self._bot_bros:
                    if random.random() < 0.01:
                        self._sender.send_privmsg(
                            "{} is my bot-bro.".format(ircmsg.name),
                            self.channel, self.max_message_length)
                        return

                if self.respond_to_trigger(ircmsg.name, ircmsg.msg):
                    return

                if ircmsg.msg.lower().find(self._nick) != -1:
                    if random.random() < 0.25:
                        choice = random.choice(self._responses)
                        choice = choice.replace("USER", ircmsg.name, 1)
                        self._sender.send_privmsg(choice, self.channel,
                                                  self.max_message_length)

                elif ircmsg.msg[:1] == self.command_prefix:
                    # No command after command prefix
                    if len(ircmsg.msg.strip()) == 1:
                        return

                    time_now = time.time()
                    if ((time_now - self._last_command_time) <
                            self._min_msg_interval):
                        logging.info(
                            "Too many commands, trigger_user: %s", ircmsg.name)
                        return

                    # Execute command
                    self.execute_command(ircmsg.name, ircmsg.msg)
                    self._last_command_time = time.time()

        elif raw_ircmsg.find("ERROR") != -1:
            logging.error(raw_ircmsg)

        elif raw_ircmsg.find("JOIN") != -1:
            # Grab user meta info similar to USERHOST
            self._user_meta = raw_ircmsg.split(maxsplit=1)[0]

            # Calculate max message length once that info is known
            self._max_message_length = self.get_max_message_length()

        elif raw_ircmsg.find("PING :") != -1:
            self.ping(raw_ircmsg)
            self._last_ping_time = time.time()

        # PRIVMSG and NOTICE with this are sometimes together
        if raw_ircmsg.find(":You are now logged in as " + self._nick) != -1:
            self.join(self.channel)

    def respond_to_trigger(self, name: str, message: str) -> bool:
        trigger_keys = list(self.triggers.keys())
        for trigger_key in trigger_keys:

            # Check if message contains trigger key
            if message.lower().find(trigger_key) != -1:

                # Check if trigger key is command
                if '.' in trigger_key:
                    # Then it must be at the beginning
                    if not message.lower().startswith(trigger_key):
                        return False

                chance = self.triggers[trigger_key][0]
                if random.random() < chance:
                    response = random.choice(self.triggers[trigger_key][1:])
                    response = response.replace('BOTNAME', self._nick)
                    response = response.replace('ADMIN', self.admin_name)
                    response = response.replace('USER', name)
                    self._sender.send_privmsg(response, self.channel,
                                              self.max_message_length)
                    return True
        return False

    def handle_user_on_message(self, name: str, message: str) -> None:
        user_q = Query()
        user_q_res = self.user_db.get(user_q.name == name)
        if not user_q_res:
            msgs: collections.deque = collections.deque(maxlen=self.user_db_message_log_size)
            msgs.append(message)
            self.user_db.insert({'name': name,
                                 'lastseen': time.time(),
                                 'lastmessage': message,
                                 'messages': list(msgs)})
        else:
            msgs = collections.deque(user_q_res['messages'],
                                     maxlen=self.user_db_message_log_size)
            msgs.append(message)
            self.user_db.update({'lastseen': time.time(),
                                 'lastmessage': message,
                                 'messages': list(msgs)
                                 }, user_q.name == name)

    def execute_command(self, name: str, message: str) -> None:
        command_name = message[1:self._max_command_length + 1]
        if not ''.join(command_name.split()):
            return
        command_name = command_name.split()[0]

        try:
            if command_name in self.commands:
                self.commands[command_name].execute([name, message])
        except Exception as e:
            logging.error(e)
