import unittest
from unittest.mock import MagicMock

from src.command import HelpCommand
from src.ircbot import IRCBot


class CommandBaseTest(unittest.TestCase):
    nick = "test_nick"
    message = "test message"

    def test_help_command(self):
        mock_bot = IRCBot()
        mock_bot.sendmsg = MagicMock()

        class_under_test = HelpCommand(mock_bot)
        class_under_test.execute([self.nick, self.message])

        mock_bot.sendmsg.assert_called_with(
            f'Use {mock_bot.command_prefix}cmds for all commands, and '
            f'{mock_bot.command_prefix}about for more info.', self.nick,
            notice=True)
