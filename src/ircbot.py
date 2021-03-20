__author__ = "Lorenz Leitner"
__version__ = "0.1337"
__license__ = "MIT"


import collections
import json
import logging
import os
import random
import select
import socket
import string
import threading
import time
from datetime import datetime
from typing import Tuple, List, Dict

from tinydb import TinyDB, Query

from src.command import HelpCommand, CommandCommand, AboutCommand, \
    LmCommand, SentimentCommand, TimeCommand, DateCommand, \
    UptimeCommand, UpdogCommand, FrequentWordsCommand, \
    WordCloudCommand, WeekdayCommand, InterjectCommand, \
    CopypastaCommand, ShrugCommand, Command
from src.settings import CONFIG

# Misc settings
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename=datetime.now().strftime(
                        '%Y_%m_%d.log'), level=logging.DEBUG)
BOT_PATH = os.path.dirname(os.path.abspath(__file__))

try:
    TERM_COLUMNS = int(os.popen('stty size', 'r').read().split()[1])
except IndexError:
    logging.warning("term columns could not be ascertained")
    TERM_COLUMNS = 80


class IRCBot:
    def __init__(self):
        # Socket
        self.ircsock_: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_timeout_ = 60*3  # 2 min pings on snoonet

        # User defined options
        self._server = CONFIG['server']
        self._channel = CONFIG['channel']
        self._nick = CONFIG['bot_nick']
        self._password = CONFIG['password']
        self._admin_name = CONFIG['admin_name']
        self._exitcode = CONFIG['exit_code'].replace('BOTNICK', self._nick, 1)
        self._command_prefix = CONFIG['command_prefix']
        self._user_db_message_log_size = CONFIG['user_db_message_log_size']
        self._user_db = TinyDB('users.json')

        # Default memvars
        self._max_user_name_length = 17  # Freenode, need to check snoonet
        self._max_message_length = 0  # Set later
        self._commands: Dict[str, Command] = self.create_commands()
        self._responses: List[str] = []
        self._bot_bros: List[str] = []
        self._triggers: Dict[str, List] = {}
        self._max_command_length = self.get_max_command_length()
        self._min_msg_interval = 1.01
        self._last_command_time = 0.0
        self._last_ping_time = time.time()
        self._re_files_txt_interval = 60.0 * 15
        self._repeated_message_sleep_time = 1.25
        self._user_meta = ""  # Set later
        self._replace_strings = ['ADMIN', 'USER', 'BOTNAME', 'COMMANDPREFIX']
        self._version = __version__
        self._join_time = 0.0
        self._join_delay = 10.0
        self._ignoring_messages = True
        self._creation_time = time.time()

    @property
    def command_prefix(self):
        return self._command_prefix

    @property
    def commands(self):
        return self._commands

    @property
    def repeated_message_sleep_time(self):
        return self._repeated_message_sleep_time

    @property
    def admin_name(self):
        return self._admin_name

    @property
    def version(self):
        return self._version

    @property
    def channel(self):
        return self._channel

    @property
    def user_db(self):
        return self._user_db

    @property
    def user_db_message_log_size(self):
        return self._user_db_message_log_size

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def triggers(self) -> Dict[str, List]:
        return self._triggers

    @property
    def max_message_length(self):
        return self._max_message_length

    def create_commands(self) -> Dict[str, Command]:
        return {
            'about': AboutCommand(self),
            'cmds': CommandCommand(self),
            'copypasta': CopypastaCommand(self),
            'date': DateCommand(self),
            'help': HelpCommand(self),
            'interject': InterjectCommand(self),
            'lastmessage': LmCommand(self),
            'sentiment': SentimentCommand(self),
            'shrug': ShrugCommand(self),
            'time': TimeCommand(self),
            'updog': UpdogCommand(self),
            'uptime': UptimeCommand(self),
            'weekday': WeekdayCommand(self),
            'wordcloud': WordCloudCommand(self),
            'words': FrequentWordsCommand(self),
        }

    def connect(self, reconnect=False):
        if reconnect:
            # self.ircsock_.close()
            self.ircsock_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.ircsock_.connect((self._server, 6667))
        except socket.gaierror as e:
            logging.error(e)
            return False

        logging.info("socket connection established")
        self.ircsock_.send(bytes("PASS " + self._password + "\n", "UTF-8"))
        self.ircsock_.send(bytes("USER " + self._nick + " " + self._nick +
                                 " " + self._nick + ":snoobotasmo .\n",
                                 "UTF-8"))
        self.ircsock_.send(bytes("NICK " + self._nick + "\n", "UTF-8"))
        logging.info("initial IRC connection successful")
        return True

    def join(self, chan):
        self.ircsock_.send(bytes("JOIN " + chan + "\n", "UTF-8"))
        self._join_time = time.time()

    def ping(self, msg):
        # PING code can be in a multiline message
        ping_code = msg[msg.rindex('PING') + len('PING :'):]
        self.ircsock_.send(bytes('PONG :' + ping_code + '\r\n', "UTF-8"))

    def sendmsg(self, msg, target, notice=False):
        # TODO: Create sender class so it can be passed to command
        # Handle sending a message that is longer than the max IRC
        # message length, i.e. split it up into multiple messages
        msg_parts = [msg[i:i + self.max_message_length]
                     for i in range(0, len(msg), self.max_message_length)]

        # NOTICE for private messages without separate buffer
        # PRIVMSG for message to buffer, either nick or channel
        irc_cmd = "NOTICE " if notice else "PRIVMSG "
        separator = " " if notice else " :"

        for msg_part in msg_parts:
            self.ircsock_.send(bytes(irc_cmd + target + separator
                                     + msg_part + "\n", "UTF-8"))
            time.sleep(self.repeated_message_sleep_time)
        return True

    def startbatch(self, channel):
        batch_id = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=14))
        # Multiline not in prod yet:
        # https://github.com/ircv3/ircv3-specifications/pull/398
        batch_type = 'draft/multiline'
        self.ircsock_.send(bytes("BATCH +" + batch_id + " " + batch_type +
                                 " " + channel + "\n", "UTF-8"))
        return batch_id

    def endbatch(self, batch_id):
        self.ircsock_.send(bytes("BATCH -" + batch_id + "\n", "UTF-8"))

    def receivemsg(self):
        # Timeout when connection is lost
        self.ircsock_.setblocking(False)
        ready = select.select([self.ircsock_], [], [], self.socket_timeout_)
        ircmsg = ""
        if ready[0]:
            try:
                ircmsg = self.ircsock_.recv(2048).decode("UTF-8")
            except (OSError, UnicodeDecodeError) as e:
                logging.error(e)
                return "ERROR"

        ircmsgs = ircmsg.split('\r\n')
        if len(ircmsgs) > 1 and not ircmsgs[len(ircmsgs) - 1]:
            del ircmsgs[len(ircmsgs) - 1]
        sepmsg = "ircmsg:"
        for ircmsg in ircmsgs:
            logging.info("%s %s", sepmsg, "-" *
                         (TERM_COLUMNS - len(sepmsg) - 30))
            logging.info(ircmsg)
        self.ircsock_.setblocking(True)
        return ircmsgs

    def get_max_command_length(self):
        max_length = 0
        for command_name in self.commands:
            if len(command_name) > max_length:
                max_length = len(command_name)
        return max_length

    def get_max_message_length(self):
        irc_max_msg_len = 512
        return irc_max_msg_len - (
                len(self._user_meta) +
                len("PRIVMSG ") +
                len(self.channel) +
                len(" :") +
                len("\n"))

    def get_responses(self) -> List[str]:
        with open(os.path.join(BOT_PATH, 'responses.txt')) as f:
            responses = f.readlines()
        responses = [r.strip() for r in responses]
        responses = [r.replace("ADMIN", self.admin_name, 1) for r in responses]
        responses = [r.replace("COMMANDPREFIX", self.command_prefix, 1)
                     for r in responses]
        return responses

    def get_bot_bros(self) -> List[str]:
        with open(os.path.join(BOT_PATH, 'bots.txt')) as f:
            bots = f.readlines()
        bots = [b.strip() for b in bots]
        return bots

    def get_triggers(self) -> Dict[str, List]:
        with open(os.path.join(BOT_PATH, 'triggers.json')) as f:
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

    def run(self):
        self.connect()

        # Thread to re-read the database files
        t_read_database = threading.Thread(
            target=self.re_read_txt_database_loop)
        t_read_database.start()

        # Thread to continuously receive and parse messages
        t_recv_parse_msg = threading.Thread(
            target=self.receive_and_parse_msg_loop)
        t_recv_parse_msg.start()

    def re_read_txt_database_loop(self):
        while True:
            read_ins = self.read_db_txt_files()
            self._responses = read_ins[0]
            self._bot_bros = read_ins[1]
            self._triggers = read_ins[2]
            time.sleep(self._re_files_txt_interval)

    def receive_and_parse_msg_loop(self):
        t = threading.currentThread()
        while getattr(t, "do_run", True):
            self.receive_and_parse_msg()

    def receive_and_parse_msg(self):
        ircmsgs = self.receivemsg()
        for ircmsg in ircmsgs:
            self.receive_and_parse_irc_msg(ircmsg)

    def check_if_ignore_messages(self):
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

    def receive_and_parse_irc_msg(self, ircmsg):
        if not ircmsg:
            logging.info("empty ircmsg possibly due to timeout/no connection")
            self.connect(reconnect=True)
            time.sleep(self.socket_timeout_ / 10)
            return

        if ircmsg.find("PRIVMSG") != -1:
            if self.check_if_ignore_messages():
                return

            name = ircmsg.split('!', 1)[0][1:]
            try:
                message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]
            except IndexError as e:
                # TODO: Use logging.exception or traceback module
                logging.error(e)
                return

            # Put user in data base or update existing user
            self.handle_user_on_message(name, message)

            if (name.lower() == self.admin_name.lower() and
                    message.rstrip() == self._exitcode):
                self.sendmsg("cya", self.channel)
                self.ircsock_.send(bytes("QUIT \n", "UTF-8"))
                return

            # Normal user messages/commands
            if len(name) < self._max_user_name_length:
                if name in self._bot_bros:
                    if random.random() < 0.01:
                        self.sendmsg(
                            "{} is my bot-bro.".format(name),
                            self.channel)
                        return

                if self.respond_to_trigger(name, message):
                    return

                if message.lower().find(self._nick) != -1:
                    if random.random() < 0.25:
                        choice = random.choice(self._responses)
                        choice = choice.replace("USER", name, 1)
                        self.sendmsg(choice, self.channel)

                elif message[:1] == self.command_prefix:
                    # No command after command prefix
                    if len(message.strip()) == 1:
                        return

                    time_now = time.time()
                    if ((time_now - self._last_command_time) <
                            self._min_msg_interval):
                        logging.info(
                            "Too many commands, trigger_user: %s", name)
                        return

                    # Execute command
                    self.execute_command(name, message)
                    self._last_command_time = time.time()

        elif ircmsg.find("ERROR") != -1:
            logging.error(ircmsg)

        elif ircmsg.find("JOIN") != -1:
            # Grab user meta info similar to USERHOST
            self._user_meta = ircmsg.split(maxsplit=1)[0]

            # Calculate max message length once that info is known
            self._max_message_length = self.get_max_message_length()

        elif ircmsg.find("PING :") != -1:
            self.ping(ircmsg)
            self._last_ping_time = time.time()

        # PRIVMSG and NOTICE with this are sometimes together
        if ircmsg.find(":You are now logged in as " + self._nick) != -1:
            self.join(self.channel)

    def respond_to_trigger(self, name, message):
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
                    self.sendmsg(response, self.channel)
                    return True
        return False

    def handle_user_on_message(self, name, message):
        user_q = Query()
        user_q_res = self.user_db.get(user_q.name == name)
        if not user_q_res:
            msgs = collections.deque(maxlen=self.user_db_message_log_size)
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

    def execute_command(self, name, message):
        command_name = message[1:self._max_command_length + 1]
        if not ''.join(command_name.split()):
            return
        command_name = command_name.split()[0]

        try:
            if command_name in self.commands:
                self.commands[command_name].execute([name, message])
        except Exception as e:
            logging.error(e)
