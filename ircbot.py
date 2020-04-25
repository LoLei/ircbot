__author__ = "Lorenz Leitner"
__version__ = "0.1337"
__license__ = "MIT"

# Todos:
# * Fix NickServ resetting nick
import logging
import os
import socket
import time
import random
import string
import threading
from datetime import datetime
from pathlib import Path
# Own
from user import User
from command import HelpCommand, CommandCommand, AboutCommand,\
    LmCommand, SentimentCommand, TimeCommand, DateCommand,\
    UptimeCommand, UpdogCommand

# Misc settings
termrows, termcolumns = os.popen('stty size', 'r').read().split()
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename=datetime.now().strftime(
                        '%Y_%m_%d.log'), level=logging.DEBUG)
HOME_DIR = str(Path.home())
BOT_DIR = os.path.join(HOME_DIR, "git/ircbot")
assert os.path.isdir(BOT_DIR)


class IRCBot():
    def __init__(self, server, channel, nick, password, adminname,
                 exitcode, command_prefix):
        self.ircsock_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_ = server
        self.channel_ = channel
        self.nick_ = nick
        self.password_ = password
        self.adminname_ = adminname
        self.exitcode_ = exitcode
        self.command_prefix_ = command_prefix
        self.users_hash_map_ = {}
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
            'updog': UpdogCommand(self)
        }
        self.responses_ = []
        self.bot_bros_ = []
        self.max_command_length_ = self.get_max_command_length()
        self.min_msg_interval_ = 1.5
        self.last_msg_time_ = 0.0
        self.re_nick_interval_ = 60.0*15
        self.re_files_txt_interval_ = 60.0*2
        self.version_ = __version__
        self.creation_time_ = time.time()

    def connect(self):
        self.ircsock_.connect((self.server_, 6667))
        self.ircsock_.send(bytes("PASS " + self.password_ + "\n", "UTF-8"))
        self.ircsock_.send(bytes("USER " + self.nick_ + " " + self.nick_ +
                                 " " + self.nick_ + ":snoobotasmo .\n",
                                 "UTF-8"))
        self.ircsock_.send(bytes("NICK " + self.nick_ + "\n", "UTF-8"))

    def join(self, chan):
        self.ircsock_.send(bytes("JOIN " + chan + "\n", "UTF-8"))

    def ping(self, msg):
        self.ircsock_.send(bytes('PONG ' + msg.split()[1] + '\r\n', "UTF-8"))

    def sendmsg(self, msg, target):
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
        ircmsg = self.ircsock_.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        sepmsg = "ircmsg:"
        logging.info("%s %s", sepmsg, "-"*(int(termcolumns)-len(sepmsg)-30))
        logging.info(ircmsg)
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
        while True:
            self.receive_and_parse_msg()

    def receive_and_parse_msg(self):
        ircmsg = self.receivemsg()

        if ircmsg.find("PRIVMSG") != -1:
            name = ircmsg.split('!', 1)[0][1:]
            message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]

            if name not in self.users_hash_map_:
                new_user = User(name, time.time(), message)
                self.users_hash_map_[name] = new_user
            else:
                self.users_hash_map_[name].last_seen_ = time.time()
                self.users_hash_map_[name].last_message_ = message

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
                    if random.random() < 0.1:
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
        elif ircmsg.find("NOTICE") != -1:
            if ircmsg.find(":You are now logged in as " +
                           self.nick_) != -1:
                self.join(self.channel_)
        elif ircmsg.find("ERROR") != -1:
            logging.error(ircmsg)
            return
