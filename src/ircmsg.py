import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger()


@dataclass
class IrcMsg:
    name: str
    channel: str
    msg: str

    @staticmethod
    def from_raw(raw: str) -> Optional['IrcMsg']:
        name = raw.split('!', 1)[0][1:]
        channel = raw.split('PRIVMSG', 1)[1].split()[0]

        try:
            msg = raw.split('PRIVMSG', 1)[1].split(':', 1)[1]
        except IndexError as e:
            # TODO: Use logging.exception or traceback module
            logging.error(e)
            return None

        return IrcMsg(name, channel, msg)
