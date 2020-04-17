# TODO: ?commands: list available commands
import os
import socket
import time
import random
# Own
from util import User
from util import LmCommand
from util import SentimentCommand

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
        self.command_prefix_ = '?'
        self.commands_ = {'lm': LmCommand(self), 'sent': SentimentCommand(self)}

    def connect(self):
        self.ircsock_.connect((self.server_, 6667))
        self.ircsock_.send(bytes("PASS " + self.password_ + "\n", "UTF-8"))
        self.ircsock_.send(bytes("USER " + self.nick_ + " " + self.nick_ +
                           " " + self.nick_ + ":snoobotasmo .\n", "UTF-8"))
        self.ircsock_.send(bytes("NICK " + self.nick_ + "\n", "UTF-8"))

    def join(self, chan):
        self.ircsock_.send(bytes("JOIN " + chan + "\n", "UTF-8"))

    def ping(self, msg):
        self.ircsock_.send(bytes('PONG ' + msg.split()[1] + '\r\n', "UTF-8"))

    def sendmsg(self, msg, target):
        self.ircsock_.send(bytes("PRIVMSG " + target + " :" + msg +
                                 "\n", "UTF-8"))

    def receivemsg(self):
        ircmsg = self.ircsock_.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        sepmsg = "ircmsg:"
        print(sepmsg, "#"*(int(termcolumns)-len(sepmsg)))
        print(ircmsg)
        return ircmsg

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

                if len(name) < 17:  # Max user name length
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

                    elif message[:5].find('?lm') != -1:
                        try:
                            arg = message.split(' ', 1)[1]
                        except IndexError:
                            self.sendmsg("I need a name.", self.channel_)
                            continue

                        # TODO: Just try to execute the string after ? directly,
                        # no need for if/switch
                        self.commands_['lm'].execute(arg)

                    elif message[:5].find('?sent') != -1:
                        try:
                            arg = message.split(' ', 1)[1]
                        except IndexError:
                            self.sendmsg("I need a name or some text.",
                                         self.channel_)
                            continue

                        self.commands_['sent'].execute(arg)

            elif ircmsg.find("PING :") != -1:
                self.ping(ircmsg)
            elif ircmsg.find("NOTICE") != -1:
                if ircmsg.find(":You are now logged in as " +
                               self.nick_) != -1:
                    self.join(self.channel_)
            elif ircmsg.find("ERROR") != -1:
                return
