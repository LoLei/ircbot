import calendar
import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import re
import time
import copypasta_search as cps
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

    @staticmethod
    def check_arg(incoming_message):
        query = incoming_message.split(' ', 1)
        try:
            query = query[1].strip()
        except IndexError:
            return False
        if query in ['', '*', '\\']:
            return False
        return query


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
        name_query = Command.check_arg(incoming_message)
        if not name_query:
            self.receiver_.sendmsg('I need a name.', self.receiver_.channel_)
            return False

        user_q = Query()
        user_q_res = self.receiver_.user_db_.search(
            user_q.name.matches(name_query, flags=re.IGNORECASE))

        if user_q_res:
            lm = user_q_res[0]['lastmessage']
            ls = user_q_res[0]['lastseen']
            msg = ("{0}\'s last message: \"{1}\" at {2}. "
                   ).format(user_q_res[0]['name'], lm, ls)
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
        name_query = Command.check_arg(incoming_message)
        if not name_query:
            self.receiver_.sendmsg('I need a name or some text.',
                                   self.receiver_.channel_)
            return False

        # Use last message of user if argument is user name,
        # and that name is in the user log
        user_q = Query()
        user_q_res = self.receiver_.user_db_.search(
            user_q.name.matches(name_query, flags=re.IGNORECASE))

        if user_q_res:
            sentiment_text = user_q_res[0]['lastmessage']

        # Else just analyze the text as is
        else:
            sentiment_text = name_query

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
        trigger_nick = args[0]
        incoming_message = args[1]
        name_query = Command.check_arg(incoming_message)
        if not name_query:
            name_query = trigger_nick

        user_q = Query()
        user_q_res = self.receiver_.user_db_.search(
            user_q.name.matches(name_query, flags=re.IGNORECASE))

        if not user_q_res:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)
            return True

        msgs = list(user_q_res[0]['messages'])
        msgs = [msg.lower() for msg in msgs]

        name = user_q_res[0]['name']

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
        msg = "({}) Most frequent words for {}: {}".format(trigger_nick, name,
                                                           top_n_str)
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class WordCloudCommand(Command):

    helptext_ = "<user> [title] generate a word cloud for a user"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        trigger_nick = args[0]
        incoming_message = args[1]
        name_query = Command.check_arg(incoming_message)
        if not name_query:
            name_query = trigger_nick

        use_title = False
        try:
            if incoming_message.split(' ')[2].strip() == "title":
                use_title = True
        except IndexError:
            pass

        user_q = Query()
        user_q_res = self.receiver_.user_db_.search(
            user_q.name.matches(name_query, flags=re.IGNORECASE))

        if not user_q_res:
            self.receiver_.sendmsg(
                "I haven't encountered this user yet.",
                self.receiver_.channel_)
            return True
        name = user_q_res[0]['name']

        msg = "({}) Cloud generation for nick {} started...".format(
                trigger_nick, name)
        self.receiver_.sendmsg(msg, self.receiver_.channel_)

        # Get all user messages as a string
        msgs = list(user_q_res[0]['messages'])
        user_text = ' '.join(msgs)

        # Add bot commands to list of stop words
        stopwords = util.STOPWORDS
        stopwords.update(self.receiver_.commands_.keys())
        stopwords.update([name, name.lower()])

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
        wc.generate(user_text.lower())

        # Create colormap from image
        image_colors = ImageColorGenerator(mask)
        plt.figure(figsize=[20, 20])
        plt.imshow(wc.recolor(color_func=image_colors),
                   interpolation="bilinear")
        plt.axis("off")
        if use_title:
            title = "Wordcloud for " + name
            plt.title(title, fontsize=36)

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


class InterjectCommand(Command):

    helptext_ = "set people right about GNU/Linux"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        msg = self.receiver_.triggers_[' linux'][1]
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True


class CopypastaCommand(Command):

    helptext_ = "<query> get copypasta based on query"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        incoming_message = args[1]
        query = Command.check_arg(incoming_message)
        if not query:
            self.receiver_.sendmsg('I need a search term.',
                                   self.receiver_.channel_)
            return False

        pasta = cps.get_copypasta(query)
        pasta = pasta[:self.receiver_.max_message_length_ - 3]
        pasta = pasta.replace('\n', ' ')
        pasta = ' '.join(pasta.split())
        pasta = pasta.strip()
        pasta += '...'
        self.receiver_.sendmsg(pasta, self.receiver_.channel_)
        return True


class ShrugCommand(Command):

    helptext_ = "make the bot shrug"

    # Receiver = Invoker
    def __init__(self, receiver):
        self.receiver_ = receiver

    def execute(self, args):
        msg = r"¯\_(ツ)_/¯"
        self.receiver_.sendmsg(msg, self.receiver_.channel_)
        return True
