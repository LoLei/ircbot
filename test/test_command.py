import unittest
from unittest.mock import MagicMock

from src.command import HelpCommand
from src.ircbot import IRCBot
from src.sender import Sender


class CommandBaseTest(unittest.TestCase):
    nick = "test_nick"
    message = "test message"

    def test_help_command(self):
        mock_bot = IRCBot()
        mock_sender = Sender(irc_socket=mock_bot._irc_sock,
                             repeated_message_sleep_time=
                             mock_bot.repeated_message_sleep_time)
        mock_sender.send_msg = MagicMock()

        class_under_test = HelpCommand(mock_bot, mock_sender)
        class_under_test.execute([self.nick, self.message])

        mock_sender.send_msg.assert_called_with(
            f'Use {mock_bot.command_prefix}cmds for all commands, and '
            f'{mock_bot.command_prefix}about for more info.',
            self.nick,
            mock_bot.max_message_length,
            notice=True)
