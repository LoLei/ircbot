#!/usr/bin/env python3

import platform

from src.ircbot import IRCBot


def main():
    # Define server, channel, nick, etc. in config.yaml
    print(f"Python version: {platform.python_version()}")
    ircbot = IRCBot()
    ircbot.run()


if __name__ == "__main__":
    main()
