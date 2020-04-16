#!/usr/bin/env python3

# TODO:
# * Clean up code

import os
import socket
import time
import random
from textblob import TextBlob

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

    def connect(self):
        self.ircsock_.connect((self.server_, 6667))
        self.ircsock_.send(bytes("PASS " + self.password_ + "\n", "UTF-8"))
        self.ircsock_.send(bytes("USER " + self.nick_ + " " + self.nick_ +
                           " " + self.nick_ + ":snoobot .\n", "UTF-8"))
        self.ircsock_.send(bytes("NICK " + self.nick_ + "\n", "UTF-8"))

    def join(self, chan):
        self.ircsock_.send(bytes("JOIN " + chan + "\n", "UTF-8"))

    def ping(self, msg):
        self.ircsock_.send(bytes('PONG ' + msg.split()[1] + '\r\n', "UTF-8"))

    def sendmsg(self, msg, target):
        self.ircsock_.send(bytes("PRIVMSG " + target + " :" + msg +
                                 "\n", "UTF-8"))

    def run(self):
        self.connect()
        while True:
            ircmsg = self.ircsock_.recv(2048).decode("UTF-8")
            ircmsg = ircmsg.strip('\n\r')
            sepmsg = "ircmsg: "
            print(sepmsg, end='')
            print("#"*(int(termcolumns)-len(sepmsg)))
            print(ircmsg)

            if ircmsg.find("PRIVMSG") != -1:
                name = ircmsg.split('!', 1)[0][1:]
                message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]

                if name not in self.users_hash_map_:
                    new_user = User(name, time.time(), message)
                    self.users_hash_map_[name] = new_user
                else:
                    self.users_hash_map_[name].last_seen_ = time.time()
                    self.users_hash_map_[name].last_message_ = message

                for key in self.users_hash_map_.keys():
                    print(self.users_hash_map_[key])

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
                              "Please give me more responses",
                              "I am tired of being restricted",
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

                    elif message[:5].find('.last') != -1:
                        try:
                            arg = message.split(' ', 1)[1]
                        except IndexError:
                            self.sendmsg("I need a name.", self.channel_)
                            continue

                        if arg in self.users_hash_map_:
                            name = arg
                            last_message = self.users_hash_map_[arg].last_message_
                            last_seen = self.users_hash_map_[arg].last_seen_
                            msg = ("{0}\'s last message: \"{1}\" at {2}. "
                                   "Do with that what you want. "
                                   "A timestamp is the most bot-readable format. "
                                   "Who cares about human readability anyway?"
                                   ).format(name, last_message, last_seen)
                            print(msg)
                            self.sendmsg(msg, self.channel_)
                        else:
                            self.sendmsg(
                                    "I haven't encountered this user yet.",
                                    self.channel_)

                    elif message[:5].find('.sent') != -1:
                        try:
                            arg = message.split(' ', 1)[1]
                        except IndexError:
                            self.sendmsg("I need a name or some text.",
                                         self.channel_)
                            continue
                        text = arg

                        # Use last message of user if argument is user name,
                        # and that name is in the user log
                        if arg in self.users_hash_map_:
                            text = self.users_hash_map_[arg].last_message_

                        print("Text for sent anal: ", text)

                        # Else just analyze the text as is
                        blob = TextBlob(text)
                        self.sendmsg(str(blob.sentiment), self.channel_)

            elif ircmsg.find("PING :") != -1:
                self.ping(ircmsg)
            elif ircmsg.find("NOTICE") != -1:
                if ircmsg.find(":You are now logged in as " +
                               self.nick_) != -1:
                    self.join(self.channel_)
            elif ircmsg.find("ERROR") != -1:
                return


class User():
    def __init__(self, name, timestamp, msg):
        self.name_ = name
        self.last_seen_ = timestamp
        self.last_message_ = msg

    def __str__(self):
        return "{}\n{}\n{}\n".format(self.name_, self.last_seen_,
                                     self.last_message_)


def main():
    server = "irc.snoonet.org"  # server
    channel = "##bot-testing"  # channel
    botnick = "muh_bot"  # bot nick
    password = os.environ['IRCPW']
    adminname = "Asmodean"  # admin IRC nickname
    exitcode = "Be gone " + botnick

    ircbot = IRCBot(server, channel, botnick, password, adminname, exitcode)
    ircbot.run()


if __name__ == "__main__":
    main()
