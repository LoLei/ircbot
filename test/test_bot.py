import unittest

from src.ircbot import IRCBot


class BotBaseTest(unittest.TestCase):

    def test_read_db_txt_files(self) -> None:
        class_under_test = IRCBot()
        file_readings = class_under_test.read_db_txt_files()
        self.assertEqual(3, len(file_readings))
