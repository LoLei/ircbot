#!/usr/bin/env python3
# https://github.com/Orderchaos/LinuxAcademy-IRC-Bot

import os
import socket
import random
from time import sleep

ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server = "irc.snoonet.org"  # server
# channel = "##bot-testing"  # channel
channel = "#linuxmasterrace"  # channel
botnick = "muh_bot"  # bot nick
password = os.environ['IRCPW']
adminname = "Asmodean"  # admin IRC nickname
exitcode = "bye " + botnick
termrows, termcolumns = os.popen('stty size', 'r').read().split()


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
                # elif message[:5].find('.tell') != -1:
                    # target = message.split(' ', 1)[1]
                    # if target.find(' ') != -1:
                        # message = target.split(' ', 1)[1]
                        # target = target.split(' ')[0]
                    # else:
                        # target = name
                        # message = "Could not parse. The message should be in the format of ‘.tell [target] [message]’ to work properly."
                    # sendmsg(message, target)
        elif ircmsg.find("PING :") != -1:
            ping(ircmsg)
        # elif ircmsg.find("NOTICE " + botnick + ":") != -1:
        elif ircmsg.find("NOTICE") != -1:
            if ircmsg.find(":You are now logged in as " + botnick) != -1:
                join(channel)
        elif ircmsg.find("ERROR") != -1:
            return


if __name__ == "__main__":
    main()
