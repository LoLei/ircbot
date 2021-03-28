import socket

import time


# TODO: Put other send method that use the irc socket (e.g. JOIN, PING) here
class Sender:
    def __init__(self, irc_socket: socket.socket,
                 repeated_message_sleep_time: float) -> None:
        self._irc_socket = irc_socket
        self._repeated_message_sleep_time = repeated_message_sleep_time

    @property
    def irc_socket(self) -> socket.socket:
        return self._irc_socket

    @irc_socket.setter
    def irc_socket(self, new_socket: socket.socket):
        self._irc_socket = new_socket

    def send_privmsg(self, msg: str, target: str, max_message_length,
                     notice: bool = False) -> bool:
        # TODO: Find way to set max_message_length in the constructor
        #  Not trivial because that value is only set after message have
        #  already been sent

        # Handle sending a message that is longer than the max IRC
        # message length, i.e. split it up into multiple messages
        msg_parts = [msg[i:i + max_message_length]
                     for i in range(0, len(msg), max_message_length)]

        # NOTICE for private messages without separate buffer
        # PRIVMSG for message to buffer, either nick or channel
        irc_cmd = "NOTICE " if notice else "PRIVMSG "
        separator = " " if notice else " :"

        for msg_part in msg_parts:
            self._irc_socket.send(bytes(irc_cmd + target + separator
                                        + msg_part + "\n", "UTF-8"))
            time.sleep(self._repeated_message_sleep_time)
        return True

    def send_auth(self, nick: str, password: str) -> int:
        self._irc_socket.send(bytes("PASS " + password + "\n", "UTF-8"))
        self._irc_socket.send(bytes("USER " + nick + " " + nick +
                                    " " + nick + ":snoobotasmo .\n",
                                    "UTF-8"))
        return self._irc_socket.send(bytes("NICK " + nick + "\n", "UTF-8"))

    def send_join(self, channel: str) -> int:
        return self._irc_socket.send(bytes("JOIN " + channel + "\n", "UTF-8"))

    def send_quit(self) -> int:
        return self._irc_socket.send(bytes("QUIT \n", "UTF-8"))

    def send_pong(self, code: str) -> int:
        return self._irc_socket.send(bytes('PONG :' + code + '\r\n', "UTF-8"))

    def send_start_batch(self, channel: str, batch_id: str, batch_type: str) -> int:
        return self._irc_socket.send(bytes("BATCH +" + batch_id + " " + batch_type +
                                           " " + channel + "\n", "UTF-8"))

    def send_end_batch(self, batch_id: str) -> int:
        return self._irc_socket.send(bytes("BATCH -" + batch_id + "\n", "UTF-8"))
