import calendar
import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import time
from abc import ABC, abstractmethod
from PIL import Image
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction import text
from textblob import TextBlob
from tinydb import Query
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
# Own
import imageuploader
import util


class Command(ABC):
    @property
    @abstractmethod
    def helptext_(self):
        pass

    @abstractmethod
    def execute(self, args):
        pass


class HelpCommand(Command):

    helptext_ = "show basic help text"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        msg = "Use {0}cmds for all commands, and {0}about for more info.".\
            format(self.receiver_.command_prefix_)
        self.receiver_.sendmsg(msg, args[0], notice=True)
        return True


class CommandCommand(Command):

    helptext_ = "[multiline] list available commands and usages"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        incoming_message = args[1]
        multiline = False

        try:
            multiline = bool(incoming_message.split(' ', 1)[1])
        except IndexError:
            pass

        if multiline:
            for name in self.receiver_.commands_:
                msg = self.receiver_.command_prefix_ + name +\
                    " - " + self.receiver_.commands_[name].helptext_
                self.receiver_.sendmsg(msg, args[0], notice=True)
                time.sleep(self.receiver_.repeated_message_sleep_time_/10)
        else:
            command_names = ""
            for name in self.receiver_.commands_:
                command_names += self.receiver_.command_prefix_ + name + " - "\
                    + self.receiver_.commands_[name].helptext_ + ' | '
            self.receiver_.sendmsg(command_names[:-3], args[0], notice=True)

        return True


class AboutCommand(Command):

    helptext_ = "show information about me"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
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

    def execute(self, args):
        incoming_message = args[1]
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

    helptext_ = "<text>/<user> analyze sentiment"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        incoming_message = args[1]
        try:
            sentiment_argument = incoming_message.split(' ', 1)[1].strip()
        except IndexError:
            self.receiver_.sendmsg("I need a name or some text.",
                                   self.receiver_.channel_)
            return False

        # Use last message of user if argument is user name,
        # and that name is in the user log
        name_query = sentiment_argument
        user_q = Query()
        user_q_res = self.receiver_.user_db_.get(user_q.name == name_query)
        if user_q_res:
            sentiment_text = user_q_res['lastmessage']

        # Else just analyze the text as is
        else:
            sentiment_text = sentiment_argument

        blob = TextBlob(sentiment_text)
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
            sentiment_text, pola_str)
        msg_textblob = "textblob: {{pol={}, subj={}}}".format(
            round(blob.sentiment.polarity, 3),
            round(blob.sentiment.subjectivity, 3))

        analyzer = SentimentIntensityAnalyzer()
        vs = analyzer.polarity_scores(sentiment_text)
        msg_vader = "vader: {}".format(vs)

        msg = msg_natural + " " + msg_textblob + " " + msg_vader

        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class FrequentWordsCommand(Command):

    helptext_ = "<user> show a user's most used words"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        incoming_message = args[1]
        try:
            name_query = incoming_message.split(' ', 1)[1].strip()
        except IndexError:
            self.receiver_.sendmsg("I need a name.",
                                   self.receiver_.channel_)
            return False

        user_q = Query()
        user_q_res = self.receiver_.user_db_.get(user_q.name == name_query)

        if not user_q_res:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)
            return True

        msgs = list(user_q_res['messages'])

        name = name_query

        # Add bot commands to list of stop words
        stopwords = util.STOPWORDS
        stopwords.update(self.receiver_.commands_.keys())
        stopwords.update([name.lower()])

        # Build count vectorizer and count top words
        n = 10
        cv = CountVectorizer(stop_words=stopwords)
        bow = cv.fit_transform(msgs)
        sums = bow.sum(axis=0)
        counts = [(word, sums[0, index])
                  for word, index in cv.vocabulary_.items()]
        counts = sorted(counts, key=lambda x: x[1], reverse=True)
        top_n = counts[:n]

        top_n_str = str(top_n)[1:-1]
        msg = "Most frequent words for {}: {}".format(name, top_n_str)
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class WordCloudCommand(Command):

    helptext_ = "<user> [title] generate a word cloud for a user"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        incoming_message = args[1]
        try:
            name_query = incoming_message.split(' ')[1].strip()
        except IndexError:
            self.receiver_.sendmsg("I need a name.",
                                   self.receiver_.channel_)
            return False

        use_title = False
        try:
            if incoming_message.split(' ')[2].strip() == "title":
                use_title = True
        except IndexError:
            pass

        user_q = Query()
        user_q_res = self.receiver_.user_db_.get(user_q.name == name_query)

        if not user_q_res:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)
            return True
        name = name_query

        msg = "({}) Cloud generation started. Wait for it...".format(
                name)
        self.receiver_.sendmsg(msg, self.receiver_.channel_)

        # Get all user messages as a string
        msgs = list(user_q_res['messages'])
        user_text = ' '.join(msgs)

        # Add bot commands to list of stop words
        stopwords = util.STOPWORDS
        stopwords.update(self.receiver_.commands_.keys())
        stopwords.update([name])

        # Get tux outline image
        mask = np.array(Image.open("images/tux.png"))

        # Generate wordcloud
        wc = WordCloud(stopwords=stopwords,
                       background_color="white",
                       mask=mask,
                       # mode="RGBA",
                       max_words=5000,
                       # max_font_size=40
                       )
        wc.generate(user_text)

        # Create colormap from image
        image_colors = ImageColorGenerator(mask)
        plt.figure(figsize=[9, 9])
        plt.imshow(wc.recolor(color_func=image_colors),
                   interpolation="bilinear")
        plt.axis("off")
        if use_title:
            title = "Wordcloud for " + name
            plt.title(title, fontsize=20)

        # Save on disk for later upload
        file_and_path = os.path.join('clouds', name + '.png')
        plt.savefig(file_and_path, format="png")

        # Upload wordcloud
        res = imageuploader.upload(file_and_path)

        os.remove(file_and_path)

        msg = "Cloud generated for " + name + ": "
        msg += res['link']
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class TimeCommand(Command):

    helptext_ = "show the time"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        self.receiver_.sendmsg(str(time.time()), self.receiver_.channel_)
        return True


class DateCommand(Command):

    helptext_ = "show the date"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        date_str = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc).isoformat(' ')
        self.receiver_.sendmsg(date_str, self.receiver_.channel_)
        return True


class WeekdayCommand(Command):

    helptext_ = "show the weekday"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        datetime.datetime.today().weekday()
        msg = calendar.day_name[datetime.datetime.today().weekday()]
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class UptimeCommand(Command):

    helptext_ = "show my age"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
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

    def execute(self, args):
        msg = "Nothing much, what's up with you?"
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True
