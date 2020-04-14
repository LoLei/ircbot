#!/usr/bin/env python3
# https://github.com/Orderchaos/LinuxAcademy-IRC-Bot

import os
import socket
from time import sleep

ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server = "irc.snoonet.org"  # server
channel = "##bot-testing"  # channel
botnick = "muh_bot"  # bot nick
password = os.environ['IRCPW']
adminname = "Asmodean"  # admin IRC nickname
exitcode = "bye " + botnick


def connect():
    ircsock.connect((server, 6667))
    ircsock.send(bytes("PASS " + password + "\n", "UTF-8"))
    ircsock.send(bytes("USER "+ botnick +" "+ botnick +" "+ botnick +":Just testing .\n", "UTF-8"))
    ircsock.send(bytes("NICK "+ botnick +"\n", "UTF-8"))


def join(chan):
    ircsock.send(bytes("JOIN " + chan + "\n", "UTF-8"))


def ping(msg):
    print("got ping: ", ping)
    ircsock.send(bytes('PONG ' + msg.split()[1] + '\r\n', "UTF-8"))


def sendmsg(msg, target=channel):
    ircsock.send(bytes("PRIVMSG " + target + " :" + msg + "\n", "UTF-8"))


def main():
    print("calling connect")
    connect()
    print("calling join")
    join(channel)
    print("starting while run")
    while True:
        ircmsg = ircsock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        print("ircmsg: ")
        print(ircmsg)

        if ircmsg.find("PRIVMSG") != -1:
            name = ircmsg.split('!', 1)[0][1:]
            message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]

            if len(name) < 17:
                if message.find('Hi ' + botnick) != -1:
                    sendmsg("Hello " + name + "!")
                if message[:5].find('.tell') != -1:
                    target = message.split(' ', 1)[1]
                    if target.find(' ') != -1:
                        message = target.split(' ', 1)[1]
                        target = target.split(' ')[0]
                    else:
                        target = name
                        message = "Could not parse. The message should be in the format of ‘.tell [target] [message]’ to work properly."
                    sendmsg(message, target)
            if name.lower() == adminname.lower() and message.rstrip() == exitcode:
                sendmsg("oh...okay. :'(")
                ircsock.send(bytes("QUIT n", "UTF-8"))
                return
        elif ircmsg.find("PING :") != -1:
            print("PING?!?!")
            ping(ircmsg)
        elif ircmsg.find("ERROR") != -1:
            print("ERROR?!?!")
            ping(ircmsg)


if __name__ == "__main__":
    main()
