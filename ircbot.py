import os
import socket
import time
import random
from textblob import TextBlob
# Own
from util import User

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

                    elif message[:5].find('.last') != -1:
                        try:
                            arg = message.split(' ', 1)[1]
                        except IndexError:
                            self.sendmsg("I need a name.", self.channel_)
                            continue

                        if arg in self.users_hash_map_:
                            name = arg
                            last_message = self.users_hash_map_[arg] \
                                .last_message_
                            last_seen = self.users_hash_map_[arg].last_seen_
                            # Yeh just mix string multiline formats to satisfy
                            # PEP8
                            msg = ("{0}\'s last message: \"{1}\" at {2}. "
                                   "Do with that what you want. "
                                   "A timestamp is the most bot-readable " +
                                   "format. "
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

                        # Else just analyze the text as is
                        blob = TextBlob(text)
                        print(blob.sentiment)
                        pola = blob.sentiment.polarity
                        # subj = blob.sentiment.subjectivity
                        pola_str = ""
                        if pola == 0.0:
                            pola_str = "neutral"
                        elif 0.0 < pola <= 0.25:
                            pola_str = "slightly positive"
                        elif 0.25 < pola <= 0.75:
                            pola_str = "positive"
                        elif 0.75 < pola <= 1.0:
                            pola_str = "very positive"
                        elif 0.0 > pola >= -0.25:
                            pola_str = "slightly negative"
                        elif -0.25 > pola >= -0.75:
                            pola_str = "negative"
                        elif -0.75 > pola >= -1.0:
                            pola_str = "very negative"

                        msg = "The text: \"{0}\" is {1}.".format(
                            text, pola_str)
                        self.sendmsg(msg, self.channel_)

            elif ircmsg.find("PING :") != -1:
                self.ping(ircmsg)
            elif ircmsg.find("NOTICE") != -1:
                if ircmsg.find(":You are now logged in as " +
                               self.nick_) != -1:
                    self.join(self.channel_)
            elif ircmsg.find("ERROR") != -1:
                return
