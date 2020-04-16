from abc import ABC, abstractmethod

class User():
    def __init__(self, name, timestamp, msg):
        self.name_ = name
        self.last_seen_ = timestamp
        self.last_message_ = msg

    def __str__(self):
        return "{}\n{}\n{}\n".format(self.name_, self.last_seen_,
                                     self.last_message_)


class Command(ABC):

    @abstractmethod
    def execute(self, arg):
        pass


class LmCommand(Command):

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg) -> None:
        if arg in self.receiver_.users_hash_map_:
            name = arg
            last_message = self.receiver_.users_hash_map_[arg] \
                .last_message_
            last_seen = self.receiver_.users_hash_map_[arg].last_seen_
            # Yeh just mix string multiline formats to satisfy
            # PEP8
            msg = ("{0}\'s last message: \"{1}\" at {2}. "
                   "Do with that what you want. "
                   "A timestamp is the most bot-readable " +
                   "format. "
                   "Who cares about human readability anyway?"
                   ).format(name, last_message, last_seen)
            self.receiver_.sendmsg(msg, self.receiver_.channel_)
        else:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)


class SentimentCommand(Command):

    def __init__(self, receiver) -> None:
        self.receiver_ = receiver

    def execute(self, arg) -> None:
        self.receiver_.do_something(self._a)
        self.receiver_.do_something_else(self._b)
