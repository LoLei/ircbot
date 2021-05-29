import logging
import os
import select
import socket
from typing import Union, List

log = logging.getLogger(__name__)


class Receiver:
    def __init__(self, irc_socket: socket.socket, socket_timeout: int) -> None:
        self._irc_socket = irc_socket
        self._socket_timeout = socket_timeout

        try:
            self._tc = int(os.popen('stty size', 'r').read().split()[1])
        except IndexError:
            log.warning("term columns could not be ascertained")
            self._tc = 80

    @property
    def irc_socket(self) -> socket.socket:
        return self._irc_socket

    @irc_socket.setter
    def irc_socket(self, new_socket: socket.socket) -> None:
        self._irc_socket = new_socket

    def receive_msg(self) -> Union[str, List[str]]:
        # Timeout when connection is lost
        self._irc_socket.setblocking(False)
        ready = select.select([self._irc_socket], [], [], self._socket_timeout)
        ircmsg = ""
        if ready[0]:
            try:
                ircmsg = self._irc_socket.recv(2048).decode("UTF-8")
            except (OSError, UnicodeDecodeError) as e:
                log.error(e)
                return "ERROR"

        ircmsgs = ircmsg.split('\r\n')
        if len(ircmsgs) > 1 and not ircmsgs[len(ircmsgs) - 1]:
            del ircmsgs[len(ircmsgs) - 1]
        sepmsg = "ircmsg:"
        for ircmsg in ircmsgs:
            log.info("%s %s", sepmsg, "-" * (self._tc - len(sepmsg) - 30))
            log.info(ircmsg)
        self._irc_socket.setblocking(True)
        return ircmsgs
