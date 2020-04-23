#!/usr/bin/env python3

import os
from ircbot import IRCBot


def main():
    server = "irc.snoonet.org"  # server
    # channel = "##bot-testing"  # channel
    channel = "#linuxmasterrace"  # channel
    botnick = "muh_bot"  # bot nick
    password = os.environ['IRCPW']
    adminname = "Asmodean"  # admin IRC nickname
    exitcode = "Be gone " + botnick
    command_prefix = '%'

    ircbot = IRCBot(server, channel, botnick, password, adminname, exitcode,
                    command_prefix)
    ircbot.run()


if __name__ == "__main__":
    main()
