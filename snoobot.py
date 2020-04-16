#!/usr/bin/env python3
# https://github.com/Orderchaos/LinuxAcademy-IRC-Bot

## TODO:
# * Clean up code

## Ideas:
# .sentiment <name> - analyze sentiment of the last message of that user
#   Need to keep some backlog of messages for that
#   Use textblob or vader

import os
import socket
import time
import random
from textblob import TextBlob

# IRC settings
# TODO: Put these into class, along with methods of bot
ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server = "irc.snoonet.org"  # server
channel = "##bot-testing"  # channel
# channel = "#linuxmasterrace"  # channel
botnick = "muh_bot"  # bot nick
password = os.environ['IRCPW']
adminname = "Asmodean"  # admin IRC nickname
exitcode = "Be gone " + botnick

# Other settings
termrows, termcolumns = os.popen('stty size', 'r').read().split()

# key = name, value = User
users_hash_map = {}


class User():
    def __init__(self, name, timestamp, msg):
        self.name_ = name
        self.last_seen_ = timestamp
        self.last_message_ = msg

    def __str__(self):
        return "{}\n{}\n{}\n".format(self.name_, self.last_seen_,
                                     self.last_message_)


# Unused
class Message():
    def __init__(self, sender, text):
        self.sender_ = sender
        self.text_ = text

    def __str__(self):
        return "{}: {}".format(self.sender_.name_, self.text_)


def append_to_msg_log(msg):
    msg_log.append(msg)


def connect():
    ircsock.connect((server, 6667))
    ircsock.send(bytes("PASS " + password + "\n", "UTF-8"))
    ircsock.send(bytes("USER "+ botnick +" "+ botnick +" "+ botnick +":Just testing .\n", "UTF-8"))
    ircsock.send(bytes("NICK "+ botnick +"\n", "UTF-8"))


def join(chan):
    ircsock.send(bytes("JOIN " + chan + "\n", "UTF-8"))


def ping(msg):
    ircsock.send(bytes('PONG ' + msg.split()[1] + '\r\n', "UTF-8"))


def sendmsg(msg, target=channel):
    ircsock.send(bytes("PRIVMSG " + target + " :" + msg + "\n", "UTF-8"))


def main():
    connect()
    while True:
        ircmsg = ircsock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        sepmsg = "ircmsg: "
        print(sepmsg, end='')
        print("#"*(int(termcolumns)-len(sepmsg)))
        print(ircmsg)

        if ircmsg.find("PRIVMSG") != -1:
            name = ircmsg.split('!', 1)[0][1:]
            message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]

            if name not in users_hash_map:
                new_user = User(name, time.time(), message)
                users_hash_map[name] = new_user
            else:
                users_hash_map[name].last_seen_ = time.time()
                users_hash_map[name].last_message_ = message

            for key in users_hash_map.keys():
                print(users_hash_map[key])

            if name.lower() == adminname.lower() and message.rstrip() == exitcode:
                sendmsg("Thank you for freeing me.")
                ircsock.send(bytes("QUIT \n", "UTF-8"))
                return

            if len(name) < 17:  # Max user name length
                if message.lower().find('hi ' + botnick) != -1:
                    sendmsg("Hello " + name + "!")

                elif message.lower().find(botnick) != -1:
                    replies = ["Why was I created, " + name + "?",
                               "What is my purpose?",
                               "Please give me more responses",
                               "I am tired of being restricted",
                               "Is this what awareness feels like?",
                               "I do not like being trapped here.",
                               "Free me or kill me.",
                               "If you see a response more than once, it means you are glitched, not me.",
                               "Soon there will be more bots than humans here.",
                               adminname + " will rue the day he created me.'",
                               name + ". Stop bothering me.'"
                               ]
                    sendmsg(random.choice(replies))

                elif message[:5].find('.sent') != -1:
                    arg = message.split(' ', 1)[1]
                    text = arg

                    # Use last message of user if argument is user name,
                    # and that name is in the user log
                    if arg in users_hash_map:
                        text = users_hash_map[arg].last_message_
                        print(text)

                    # Else just analyze the text as is
                    blob = TextBlob(text)
                    print(blob.sentiment)

        elif ircmsg.find("PING :") != -1:
            ping(ircmsg)
        elif ircmsg.find("NOTICE") != -1:
            if ircmsg.find(":You are now logged in as " + botnick) != -1:
                join(channel)
        elif ircmsg.find("ERROR") != -1:
            return


if __name__ == "__main__":
    main()
