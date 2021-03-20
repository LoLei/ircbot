import unittest

from unittest.mock import MagicMock

from src.command import HelpCommand
from src.ircbot import IRCBot


class CommandTest(unittest.TestCase):
    nick = "test_nick"
    message = "test message"

    def test_help_command(self):
        mock_bot = IRCBot()
        mock_bot.sendmsg = MagicMock()

        class_under_test = HelpCommand(mock_bot)
        class_under_test.execute([self.nick, self.message])

        mock_bot.sendmsg.assert_called_with('Use \\cmds for all commands, and '
                                            '\\about for more info.', self.nick,
                                            notice=True)
