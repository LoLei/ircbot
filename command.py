import datetime
import time
from abc import ABC, abstractmethod
from textblob import TextBlob


class Command(ABC):
    @property
    @abstractmethod
    def helptext_(self):
        pass

    @abstractmethod
    def execute(self, arg):
        pass


class HelpCommand(Command):

    helptext_ = "show basic help text"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        msg = "Use {0}cmds for all commands, and {0}about for more info.".\
            format(self.receiver_.command_prefix_)
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class CommandCommand(Command):

    helptext_ = "[multiline] list available commands and usages"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        incoming_message = arg
        multiline = False

        try:
            arg = incoming_message.split(' ', 1)[1]
            multiline = bool(arg)
        except IndexError:
            pass

        if multiline:
            for name in self.receiver_.commands_:
                msg = self.receiver_.command_prefix_ + name +\
                    " - " + self.receiver_.commands_[name].helptext_
                self.receiver_.sendmsg(msg, self.receiver_.channel_)
        else:
            command_names = ""
            for name in self.receiver_.commands_:
                command_names += self.receiver_.command_prefix_ + name + " - "\
                    + self.receiver_.commands_[name].helptext_ + ' | '
            self.receiver_.sendmsg(command_names[:-3], self.receiver_.channel_)

        return True


class AboutCommand(Command):

    helptext_ = "show information about me"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        msg = "I am a smol IRC bot made by " +\
            self.receiver_.adminname_ +\
            ". Mention me by name or use " +\
            self.receiver_.command_prefix_ +\
            " for commands. " +\
            "Version " + self.receiver_.version_ +\
            ". Source: https://git.io/JfJ9B"
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class LmCommand(Command):

    helptext_ = "<user> show information about last message of a user"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        incoming_message = arg
        try:
            name = incoming_message.split(' ')[1]
        except IndexError:
            self.receiver_.sendmsg("I need a name.", self.receiver_.channel_)
            return False

        case_insensitive = False
        if len(incoming_message.split(' ')) > 2:
            case_insensitive = True

        # Case insensitive dict lookup
        # Unfortunately the entire dict needs to be recreated
        query = name
        users = self.receiver_.users_hash_map_.copy()
        if case_insensitive:
            users = {k.lower(): v for k, v in users.items()}
            query = name.lower()
        for k, v in users.items():

        if query in users:
            name = users[query].name_
            last_message = self.receiver_.users_hash_map_[name] \
                .last_message_
            last_seen = self.receiver_.users_hash_map_[name].last_seen_
            msg = ("{0}\'s last message: \"{1}\" at {2}. "
                   ).format(name, last_message, last_seen)
            self.receiver_.sendmsg(msg, self.receiver_.channel_)
        else:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)
        return True


class SentimentCommand(Command):

    helptext_ = "<text>/<user> analyze sentiment of a custom text or " +\
        "a user's last message"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
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


class TimeCommand(Command):

    helptext_ = "show the time"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        self.receiver_.sendmsg(str(time.time()), self.receiver_.channel_)
        return True


class DateCommand(Command):

    helptext_ = "show the date"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        date_str = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc).isoformat(' ')
        self.receiver_.sendmsg(date_str, self.receiver_.channel_)
        return True


class UptimeCommand(Command):

    helptext_ = "show my age"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        time_now = time.time()
        diff_sec = time_now - self.receiver_.creation_time_
        diff_time = datetime.timedelta(seconds=int(diff_sec))
        self.receiver_.sendmsg(str(diff_time), self.receiver_.channel_)
        return True


class UpdogCommand(Command):

    helptext_ = "is it me or does it smell like updog in here"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        msg = "Nothing much, what's up with you?"
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True
