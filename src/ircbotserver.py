import platform

from src.ircbot import IRCBot


def main() -> None:
    # Define server, channel, nick, etc. in config.yaml
    print(f"Python version: {platform.python_version()}")
    irc_bot = IRCBot()
    irc_bot.run()
