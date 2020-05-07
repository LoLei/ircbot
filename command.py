import datetime
import os
import time
from abc import ABC, abstractmethod
from sklearn.feature_extraction.text import CountVectorizer
from textblob import TextBlob
from tinydb import Query
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
# Own
from imageuploader import ImageUploader


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
            name_query = incoming_message.split(' ')[1]
        except IndexError:
            self.receiver_.sendmsg("I need a name.", self.receiver_.channel_)
            return False

        # Currently unused again after switching to user db
        case_insensitive = False
        if len(incoming_message.split(' ')) > 2:
            case_insensitive = True

        user_q = Query()
        user_q_res = self.receiver_.user_db_.get(user_q.name == name_query)

        if user_q_res:
            lm = user_q_res['lastmessage']
            ls = user_q_res['lastseen']
            msg = ("{0}\'s last message: \"{1}\" at {2}. "
                   ).format(name_query, lm, ls)
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
        name_query = arg
        user_q = Query()
        user_q_res = self.receiver_.user_db_.get(user_q.name == name_query)
        if user_q_res:
            text = user_q_res['lastmessage']

        # Else just analyze the text as is
        blob = TextBlob(text)
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

        msg_natural = "The text: \"{0}\" is {1}.".format(
            text, pola_str)
        msg_textblob = "textblob: {{pol={}, subj={}}}".format(
            round(blob.sentiment.polarity, 3),
            round(blob.sentiment.subjectivity, 3))

        analyzer = SentimentIntensityAnalyzer()
        vs = analyzer.polarity_scores(text)
        msg_vader = "vader: {}".format(vs)

        msg = msg_natural + " " + msg_textblob + " " + msg_vader

        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class FrequentWordsCommand(Command):

    helptext_ = "show a user's most used words"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        incoming_message = arg
        try:
            arg = incoming_message.split(' ', 1)[1].strip()
        except IndexError:
            self.receiver_.sendmsg("I need a name.",
                                   self.receiver_.channel_)
            return False

        name_query = arg
        user_q = Query()
        user_q_res = self.receiver_.user_db_.get(user_q.name == name_query)

        if not user_q_res:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)
            return True

        msgs = list(user_q_res['messages'])

        n = 10
        cv = CountVectorizer(stop_words='english')
        bow = cv.fit_transform(msgs)
        sums = bow.sum(axis=0)
        counts = [(word, sums[0, index])
                  for word, index in cv.vocabulary_.items()]
        counts = sorted(counts, key=lambda x: x[1], reverse=True)
        top_n = counts[:n]

        top_n_str = str(top_n)[1:-1]
        msg = "Most frequent words for {}: {}".format(name_query, top_n_str)
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class WordCloudCommand(Command):

    helptext_ = "generate a word cloud for a user"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, arg):
        incoming_message = arg
        try:
            arg = incoming_message.split(' ', 1)[1].strip()
        except IndexError:
            self.receiver_.sendmsg("I need a name.",
                                   self.receiver_.channel_)
            return False

        name_query = arg
        user_q = Query()
        user_q_res = self.receiver_.user_db_.get(user_q.name == name_query)

        if not user_q_res:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)
            return True

        # Get all user messages as a string
        name = name_query
        msgs = list(user_q_res['messages'])
        text = ' '.join(msgs)

        # Add bot commands to list of stop words
        stopwords = set(STOPWORDS)
        stopwords.update(self.receiver_.commands_.keys())
        stopwords.update([name])

        # Generate wordcloud
        wordloud = WordCloud(stopwords=stopwords).generate(text)
        file_and_path = os.path.join('clouds', name + '.png')
        wordloud.to_file(file_and_path)

        # Upload wordcloud
        # This could be singleton or saved in invoker instance
        # As to avoid recreation
        client_id = os.environ['IMGUR_CLIENT_ID']
        client_secret = os.environ['IMGUR_CLIENT_SECRET']
        uploader = ImageUploader(client_id, client_secret)
        res = uploader.upload(file_and_path)

        msg = "Cloud generated for " + name + ": "
        msg += res['link']
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
