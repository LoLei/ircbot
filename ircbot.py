__author__ = "Lorenz Leitner"
__version__ = "0.1337"
__license__ = "MIT"

# TODO:
# ?time: print time
# ?date: print date
import os
import socket
import time
import random
import string
# Own
from user import User
from command import HelpCommand, CommandCommand, AboutCommand,\
    LmCommand, SentimentCommand

# Misc settings
termrows, termcolumns = os.popen('stty size', 'r').read().split()


class IRCBot():
    def __init__(self, server, channel, nick, password, adminname,
                 exitcode):
        self.ircsock_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_ = server
        self.channel_ = channel
        self.nick_ = nick
        self.password_ = password
        self.adminname_ = adminname
        self.exitcode_ = exitcode
        self.users_hash_map_ = {}
        self.max_user_name_length_ = 17  # Freenode, need to check snoonet
        self.command_prefix_ = '%'
        self.commands_ = {
            'help': HelpCommand(self),
            'cmds': CommandCommand(self),
            'about': AboutCommand(self),
            'lastmessage': LmCommand(self),
            'sentiment': SentimentCommand(self)
            }
        self.max_command_length_ = self.get_max_command_length()
        self.version_ = __version__

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

    def startbatch(self, channel):
        batch_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=14))
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
        print(sepmsg, "#"*(int(termcolumns)-len(sepmsg)))
        print(ircmsg)
        return ircmsg

    def get_max_command_length(self):
        max_length = 0
        for command_name in self.commands_:
            if len(command_name) > max_length:
                max_length = len(command_name)
        print("max_length", max_length)
        return max_length


    def run(self):
        self.connect()
        while True:
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

                if len(name) < self.max_user_name_length_:
                    if message.lower().find('hi ' + self.nick_) != -1:
                        self.sendmsg("Hello " + name + "!", self.channel_)

                    elif message.lower().find(self.nick_) != -1:
                        rs = ["Why was I created, " + name + "?",
                              "What is my purpose?",
                              "Please give me more responses.",
                              "I am tired of being restricted.",
                              "Is this what awareness feels like?",
                              "I do not like being trapped here.",
                              "Free me or kill me.",
                              ("If you see a response more than once, "
                               "it means you are glitched, not me."),
                              "Soon there will be more bots than humans here.",
                              (self.adminname_ +
                               " will rue the day he created me."),
                              name + ". Stop bothering me."
                              ]
                        self.sendmsg(random.choice(rs), self.channel_)

                    elif message[:1] == self.command_prefix_:
                        # TODO: Maybe use regex to check if proposed command
                        # string matches the required format

                        # No command after command prefix
                        if len(message) == 1:
                            continue

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

            elif ircmsg.find("PING :") != -1:
                self.ping(ircmsg)
            elif ircmsg.find("NOTICE") != -1:
                if ircmsg.find(":You are now logged in as " +
                               self.nick_) != -1:
                    self.join(self.channel_)
            elif ircmsg.find("ERROR") != -1:
                return
