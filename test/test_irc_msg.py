import unittest

from src.ircmsg import IrcMsg


class IrcMsgTest(unittest.TestCase):
    def test_irc_message_parsing(self) -> None:
        raw = ":SomeNick!SomeNick@snoonet.org/user/SomeNick PRIVMSG #linuxmasterrace :hello world"
        result = IrcMsg.from_raw(raw)
        print("RES", result)
        expected = IrcMsg(name="SomeNick",
                          channel="#linuxmasterrace",
                          msg="hello world")
        self.assertEqual(result, expected)

    def test_irc_message_parsing_pm(self) -> None:
        raw = ":SomeNick!SomeNick@snoonet.org/user/SomeNick PRIVMSG muh_bot :hello world"
        result = IrcMsg.from_raw(raw)
        print("RES", result)
        expected = IrcMsg(name="SomeNick",
                          channel="muh_bot",
                          msg="hello world")
        self.assertEqual(result, expected)

    def test_irc_message_parsing_fail(self) -> None:
        raw = ":SomeNick!SomeNick@snoonet.org/user/SomeNick muh_bot :hello world"
        self.assertRaises(IndexError, IrcMsg.from_raw, raw=raw)
