__author__ = "Lorenz Leitner"
__version__ = "0.1337"
__license__ = "MIT"

# Todos:
# * hex converter
# * \rant
# * Convert many class constructor parameters and environment variables to a
#   config file (YAML)
import collections
import logging
import os
import random
import select
import socket
import string
import threading
import time
from datetime import datetime
from pathlib import Path
from tinydb import TinyDB, Query
# Own
from command import HelpCommand, CommandCommand, AboutCommand,\
    LmCommand, SentimentCommand, TimeCommand, DateCommand,\
    UptimeCommand, UpdogCommand, FrequentWordsCommand,\
    WordCloudCommand
from settings import CONFIG

# Misc settings
termrows, termcolumns = os.popen('stty size', 'r').read().split()
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename=datetime.now().strftime(
                        '%Y_%m_%d.log'), level=logging.DEBUG)
HOME_DIR = str(Path.home())
BOT_DIR = os.path.join(HOME_DIR, "git/ircbot")
assert os.path.isdir(BOT_DIR)


class IRCBot():
    def __init__(self):
        self.ircsock_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_timeout_ = 60*3  # 2 min pings on snoonet
        self.server_ = CONFIG['server']
        self.channel_ = CONFIG['channel']
        self.nick_ = CONFIG['bot_nick']
        self.password_ = CONFIG['password']
        self.adminname_ = CONFIG['admin_name']
        self.exitcode_ = CONFIG['exit_code'].replace('BOTNICK', self.nick_, 1)
        self.command_prefix_ = CONFIG['command_prefix']
        self.user_db_ = TinyDB('users.json')
        self.user_db_message_log_size_ = 1000
        self.max_user_name_length_ = 17  # Freenode, need to check snoonet
        self.commands_ = {
            'help': HelpCommand(self),
            'cmds': CommandCommand(self),
            'about': AboutCommand(self),
            'lastmessage': LmCommand(self),
            'sentiment': SentimentCommand(self),
            'time': TimeCommand(self),
            'date': DateCommand(self),
            'uptime': UptimeCommand(self),
            'updog': UpdogCommand(self),
            'words': FrequentWordsCommand(self),
            'wordcloud': WordCloudCommand(self)
        }
        self.responses_ = []
        self.bot_bros_ = []
        self.max_command_length_ = self.get_max_command_length()
        self.min_msg_interval_ = 1.5
        self.last_msg_time_ = 0.0
        self.last_ping_time_ = time.time()
        self.re_files_txt_interval_ = 60.0*15
        self.version_ = __version__
        self.creation_time_ = time.time()

    def connect(self, reconnect=False):
        if reconnect:
            # self.ircsock_.close()
            self.ircsock_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.ircsock_.connect((self.server_, 6667))
        except socket.gaierror as e:
            logging.error(e)
            return False

        logging.info("socket connection established")
        self.ircsock_.send(bytes("PASS " + self.password_ + "\n", "UTF-8"))
        self.ircsock_.send(bytes("USER " + self.nick_ + " " + self.nick_ +
                                 " " + self.nick_ + ":snoobotasmo .\n",
                                 "UTF-8"))
        self.ircsock_.send(bytes("NICK " + self.nick_ + "\n", "UTF-8"))
        logging.info("initial IRC connection successful")
        return True

    def join(self, chan):
        self.ircsock_.send(bytes("JOIN " + chan + "\n", "UTF-8"))

    def ping(self, msg):
        # PING code can be in a multiline message
        ping_code = msg[msg.rindex('PING') + len('PING :'):]
        self.ircsock_.send(bytes('PONG :' + ping_code + '\r\n', "UTF-8"))

    def sendmsg(self, msg, target):
        # TODO: Handle sending a message that is longer than the max IRC message
        #       length, i.e. split it up into multiple messages
        self.ircsock_.send(bytes("PRIVMSG " + target + " :" + msg +
                                 "\n", "UTF-8"))
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
        # TODO: Handle more or less than one incoming message in the stream of
        #       bytes in one call of receivemsg
        # Timeout when connection is lost
        self.ircsock_.setblocking(False)
        ready = select.select([self.ircsock_], [], [], self.socket_timeout_)
        ircmsg = ""
        if ready[0]:
            try:
                ircmsg = self.ircsock_.recv(2048).decode("UTF-8")
            except OSError as e:
                logging.error(e)
                return ircmsg
        ircmsg = ircmsg.strip('\n\r')
        sepmsg = "ircmsg:"
        logging.info("%s %s", sepmsg, "-"*(int(termcolumns)-len(sepmsg)-30))
        logging.info(ircmsg)
        self.ircsock_.setblocking(True)
        return ircmsg

    def get_max_command_length(self):
        max_length = 0
        for command_name in self.commands_:
            if len(command_name) > max_length:
                max_length = len(command_name)
        return max_length

    def get_responses(self):
        with open(os.path.join(BOT_DIR, 'responses.txt')) as f:
            responses = f.readlines()
        responses = [r.strip() for r in responses]
        responses = [r.replace("ADMIN", self.adminname_, 1) for r in responses]
        responses = [r.replace("COMMANDPREFIX", self.command_prefix_, 1)
                     for r in responses]
        return responses

    def get_bot_bros(self):
        with open(os.path.join(BOT_DIR, 'bots.txt')) as f:
            bots = f.readlines()
        bots = [b.strip() for b in bots]
        return bots

    def read_db_txt_files(self):
        return self.get_responses(), self.get_bot_bros()

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
            self.responses_, self.bot_bros_ = self.read_db_txt_files()
            time.sleep(self.re_files_txt_interval_)

    def receive_and_parse_msg_loop(self):
        t = threading.currentThread()
        while getattr(t, "do_run", True):
            self.receive_and_parse_msg()

    def receive_and_parse_msg(self):
        ircmsg = self.receivemsg()

        if not ircmsg:
            logging.info("empty ircmsg possibly due to timeout/no connection")
            self.connect(reconnect=True)
            time.sleep(self.socket_timeout_ / 10)
            return

        if ircmsg.find("PRIVMSG") != -1:
            name = ircmsg.split('!', 1)[0][1:]
            message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]

            # TODO: Put this in function
            user_q = Query()
            user_q_res = self.user_db_.get(user_q.name == name)
            if not user_q_res:
                msgs = collections.deque(maxlen=self.user_db_message_log_size_)
                msgs.append(message)
                self.user_db_.insert({'name': name,
                                      'lastseen': time.time(),
                                      'lastmessage': message,
                                      'messages': list(msgs)})
            else:
                msgs = collections.deque(user_q_res['messages'],
                                         maxlen=self.user_db_message_log_size_)
                msgs.append(message)
                self.user_db_.update({'lastseen': time.time(),
                                      'lastmessage': message,
                                      'messages': list(msgs)
                                      }, user_q.name == name)

            if (name.lower() == self.adminname_.lower() and
                    message.rstrip() == self.exitcode_):
                self.sendmsg("Thank you for freeing me.", self.channel_)
                self.ircsock_.send(bytes("QUIT \n", "UTF-8"))
                return

            # Normal user messages/commands
            if len(name) < self.max_user_name_length_:
                time_now = time.time()
                if (time_now - self.last_msg_time_) < self.min_msg_interval_:
                    logging.info(
                        "Too many interactions, trigger_user: %s", name)
                    return
                if name in self.bot_bros_:
                    if random.random() < 0.01:
                        self.sendmsg(
                            "{} is my bot-bro.".format(name),
                            self.channel_)

                elif message.lower().find(self.nick_) != -1:
                    if random.random() < 0.75:
                        choice = random.choice(self.responses_)
                        choice = choice.replace("USER", name, 1)
                        self.sendmsg(choice, self.channel_)

                elif message[:1] == self.command_prefix_:
                    # No command after command prefix
                    if len(message) == 1:
                        return

                    # Execute command
                    command_name = message[1:self.max_command_length_+1].\
                        split()[0]
                    if command_name in self.commands_:
                        self.commands_[command_name].execute(message)
                    else:
                        self.sendmsg("Command does not exist. " +
                                     "Use {}cmds for a list.".
                                     format(self.command_prefix_),
                                     self.channel_)

                self.last_msg_time_ = time.time()

        elif ircmsg.find("PING :") != -1:
            self.ping(ircmsg)
            self.last_ping_time_ = time.time()
        elif ircmsg.find("NOTICE") != -1:
            if ircmsg.find(":You are now logged in as " +
                           self.nick_) != -1:
                self.join(self.channel_)
        elif ircmsg.find("ERROR") != -1:
            logging.error(ircmsg)
