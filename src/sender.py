import socket

#
# def sendmsg(self, irc_socket: socket.socket, msg: str, target: str,
#             max_message_length: int, repeated_message_sleep_time: int,
#             notice: bool = False) -> bool:
import time


class Sender:
    def __init__(self, irc_socket: socket.socket,
                 repeated_message_sleep_time: float) -> None:
        self._irc_socket = irc_socket
        self._repeated_message_sleep_time = repeated_message_sleep_time

    def send_msg(self, msg: str, target: str, max_message_length,
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
