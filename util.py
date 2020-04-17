from abc import ABC, abstractmethod
from textblob import TextBlob


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
        incoming_message = arg
        try:
            arg = incoming_message.split(' ', 1)[1]
        except IndexError:
            self.receiver_.sendmsg("I need a name.", self.receiver_.channel_)
            return False

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
        return True


class SentimentCommand(Command):

    # Receiver = Invoker
    def __init__(self, receiver) -> None:
        self.receiver_ = receiver

    def execute(self, arg) -> None:
        incoming_message = arg
        try:
            arg = incoming_message.split(' ', 1)[1]
        except IndexError:
            self.receiver_.sendmsg("I need a name or some text.",
                                   self.receiver_.channel_)
            return False

        text = arg

        # Use last message of user if argument is user name,
        # and that name is in the user log
        if arg in self.receiver_.users_hash_map_:
            text = self.receiver_.users_hash_map_[arg].last_message_

        # Else just analyze the text as is
        blob = TextBlob(text)
        print(blob.sentiment)
        pola = blob.sentiment.polarity
        # subj = blob.sentiment.subjectivity
        pola_str = ""
        if pola == 0.0:
            pola_str = "neutral"
        elif 0.0 < pola <= 0.25:
            pola_str = "slightly positive"
        elif 0.25 < pola <= 0.75:
            pola_str = "positive"
        elif 0.75 < pola <= 1.0:
            pola_str = "very positive"
        elif 0.0 > pola >= -0.25:
            pola_str = "slightly negative"
        elif -0.25 > pola >= -0.75:
            pola_str = "negative"
        elif -0.75 > pola >= -1.0:
            pola_str = "very negative"

        msg = "The text: \"{0}\" is {1}.".format(
            text, pola_str)
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True
