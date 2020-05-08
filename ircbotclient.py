#!/usr/bin/env python3

from ircbot import IRCBot


def main():
    # Define server, channel, nick, etc. in config.yaml
    # TODO: Make a CLI
    ircbot = IRCBot()
    ircbot.run()


if __name__ == "__main__":
    main()
