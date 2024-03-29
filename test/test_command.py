import unittest
from unittest.mock import MagicMock

from src.command import HelpCommand, CopypastaCommand
from src.ircbot import IRCBot
from src.sender.sender import Sender


class CommandBaseTest(unittest.TestCase):
    nick = "test_nick"

    def test_help_command(self) -> None:
        mock_bot = IRCBot()
        mock_sender = Sender(
            irc_socket=mock_bot._irc_sock,
            repeated_message_sleep_time=mock_bot.repeated_message_sleep_time)
        mock_sender.send_privmsg = MagicMock()

        class_under_test = HelpCommand(mock_bot, mock_sender)
        class_under_test.execute([self.nick, 'help'])

        mock_sender.send_privmsg.assert_called_with(
            f'Use {mock_bot.command_prefix}cmds for all commands, and '
            f'{mock_bot.command_prefix}about for more info.',
            self.nick,
            mock_bot.max_message_length,
            notice=True)

    def test_copypasta_command_truncate(self) -> None:
        mock_bot = IRCBot()
        mock_bot._max_message_length = 100
        mock_bot._channel = '#test'
        mock_sender = Sender(
            irc_socket=mock_bot._irc_sock,
            repeated_message_sleep_time=mock_bot.repeated_message_sleep_time)
        mock_sender.send_privmsg = MagicMock()

        class_under_test = CopypastaCommand(mock_bot, mock_sender)
        class_under_test.execute(
            [self.nick, "copypasta I'd just like to interject for a moment"])

        expected_output = "I'd just like to interject for a moment. What you’re referring to as Copilot, is in fact, GPL/Copil…"
        self.assertLessEqual(len(expected_output), 100)
        mock_sender.send_privmsg.assert_any_call(expected_output, '#test',
                                                 mock_bot.max_message_length)

    def test_copypasta_command_short(self) -> None:
        mock_bot = IRCBot()
        mock_bot._max_message_length = 100
        mock_bot._channel = '#test'
        mock_sender = Sender(
            irc_socket=mock_bot._irc_sock,
            repeated_message_sleep_time=mock_bot.repeated_message_sleep_time)
        mock_sender.send_privmsg = MagicMock()

        class_under_test = CopypastaCommand(mock_bot, mock_sender)
        class_under_test.execute(
            [self.nick, 'copypasta The shortest copypasta ever'])

        expected_output = 'ass'
        self.assertLessEqual(len(expected_output), 100)
        mock_sender.send_privmsg.assert_any_call(expected_output, '#test',
                                                 mock_bot.max_message_length)
