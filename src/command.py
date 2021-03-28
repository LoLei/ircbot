import calendar
import datetime
import os
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Union

import copypasta_search as cps
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.feature_extraction.text import CountVectorizer
from textblob import TextBlob
from tinydb import Query
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud, ImageColorGenerator

from src.imageuploader import upload
from src.sender.sender import Sender
from src.util import STOPWORDS


class Command(ABC):
    # Receiver = Invoker
    def __init__(self, receiver, sender: Sender) -> None:
        self._receiver = receiver
        self._sender = sender  # TODO: Make this the receiver
        # TODO: Remove old receiver
        # TODO: Put other properties the commands need in their own init methods

    @property
    @abstractmethod
    def help_text(self) -> str:
        pass

    @abstractmethod
    def execute(self, args: List[str]) -> bool:
        pass

    @staticmethod
    def check_arg(incoming_message: str) -> Union[str, bool]:
        try:
            query = incoming_message.split(' ', 1)[1].strip()
        except IndexError:
            return False

        if query in ['', '*', '\\']:
            return False
        return query


class HelpCommand(Command):

    @property
    def help_text(self) -> str:
        return "show basic help text"

    def execute(self, args: List[str]) -> bool:
        msg = "Use {0}cmds for all commands, and {0}about for more info.". \
            format(self._receiver.command_prefix)
        self._sender.send_privmsg(msg, args[0],
                                  self._receiver.max_message_length,
                                  notice=True)
        return True


class CommandCommand(Command):

    @property
    def help_text(self) -> str:
        return "[multiline] list available commands and usages"

    def execute(self, args: List[str]) -> bool:
        incoming_message = args[1]
        multiline = False

        try:
            multiline = bool(incoming_message.split(' ', 1)[1])
        except IndexError:
            pass

        if multiline:
            for name in self._receiver.commands:
                msg = self._receiver.command_prefix + name + \
                      " - " + self._receiver.commands[name].help_text
                self._sender.send_privmsg(msg, args[0],
                                          self._receiver.max_message_length,
                                          notice=True)
                time.sleep(self._receiver.repeated_message_sleep_time / 10)
        else:
            command_names = ""
            for name in self._receiver.commands:
                command_names += (self._receiver.command_prefix
                                  + name + " - "
                                  + self._receiver.commands[name].help_text
                                  + ' | ')
            self._sender.send_privmsg(command_names[:-3], args[0],
                                      self._receiver.max_message_length,
                                      notice=True)

        return True


class AboutCommand(Command):

    @property
    def help_text(self) -> str:
        return "show information about me"

    def execute(self, args: List[str]) -> bool:
        msg = "I am a smol IRC bot made by " + \
              self._receiver.admin_name + \
              ". Mention me by name or use " + \
              self._receiver.command_prefix + \
              " for commands. " + \
              "Version " + self._receiver.version + \
              ". Source: https://git.io/JfJ9B"
        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class LmCommand(Command):

    @property
    def help_text(self) -> str:
        return "<user> show information about last message of a user"

    def execute(self, args: List[str]) -> bool:
        incoming_message = args[1]
        name_query = Command.check_arg(incoming_message)
        if not name_query:
            self._sender.send_privmsg('I need a name.', self._receiver.channel,
                                      self._receiver.max_message_length)
            return False

        user_q = Query()
        user_q_res = self._receiver.user_db.search(
            user_q.name.matches(name_query, flags=re.IGNORECASE))

        if user_q_res:
            lm = user_q_res[0]['lastmessage']
            ls = user_q_res[0]['lastseen']
            msg = ("{0}\'s last message: \"{1}\" at {2}. "
                   ).format(user_q_res[0]['name'], lm, ls)
            self._sender.send_privmsg(msg, self._receiver.channel,
                                      self._receiver.max_message_length)
        else:
            self._sender.send_privmsg(
                "I haven't encountered this user yet.",
                self._receiver.channel,
                self._receiver.max_message_length)

        return True


class SentimentCommand(Command):

    @property
    def help_text(self) -> str:
        return "<text>/<user> analyze sentiment"

    def execute(self, args: List[str]) -> bool:
        incoming_message = args[1]
        name_query = Command.check_arg(incoming_message)
        if not name_query:
            self._sender.send_privmsg('I need a name or some text.',
                                      self._receiver.channel,
                                      self._receiver.max_message_length)
            return False

        # Use last message of user if argument is user name,
        # and that name is in the user log
        user_q = Query()
        user_q_res = self._receiver.user_db.search(
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

        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class FrequentWordsCommand(Command):

    @property
    def help_text(self) -> str:
        return "<user> show a user's most used words"

    def execute(self, args: List[str]) -> bool:
        trigger_nick = args[0]
        incoming_message = args[1]
        name_query = Command.check_arg(incoming_message)
        if not name_query:
            name_query = trigger_nick

        user_q = Query()
        user_q_res = self._receiver.user_db.search(
            user_q.name.matches(name_query, flags=re.IGNORECASE))

        if not user_q_res:
            self._sender.send_privmsg(
                "I haven't encountered this user yet.",
                self._receiver.channel, self._receiver.max_message_length)
            return True

        msgs = list(user_q_res[0]['messages'])
        msgs = [msg.lower() for msg in msgs]

        name = user_q_res[0]['name']

        # Add bot commands to list of stop words
        stopwords = STOPWORDS
        stopwords.update(self._receiver.commands.keys())
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

        msg = "({}) Top words (of last {} messages) for {}: {}".format(
            trigger_nick, self._receiver.user_db_message_log_size,
            name, self.format_count_list(top_n))
        self._sender.send_privmsg(msg, self._receiver.channel, self._receiver.max_message_length)
        return True

    @staticmethod
    def insert_zero_width_space(word: str) -> str:
        # Also make it bold
        return '\x02' + word[:1] + '\u200b' + word[1:] + '\x02'

    @staticmethod
    def format_count_list(top_n: List[Tuple[str, int]]) -> str:
        s = ""
        for (w, c) in top_n:
            s += FrequentWordsCommand \
                     .insert_zero_width_space(w) + ": " + str(c) + ", "
        return s[:-2]


class WordCloudCommand(Command):

    @property
    def help_text(self) -> str:
        return "<user> [title] generate a word cloud for a user"

    def execute(self, args: List[str]) -> bool:
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
        user_q_res = self._receiver.user_db.search(
            user_q.name.matches(name_query, flags=re.IGNORECASE))

        if not user_q_res:
            self._sender.send_privmsg(
                "I haven't encountered this user yet.",
                self._receiver.channel, self._receiver.max_message_length)
            return True
        name = user_q_res[0]['name']

        msg = "({}) Cloud generation for nick {} started...".format(
            trigger_nick, name)
        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)

        # Get all user messages as a string
        msgs = list(user_q_res[0]['messages'])
        user_text = ' '.join(msgs)

        # Add bot commands to list of stop words
        stopwords = STOPWORDS
        stopwords.update(self._receiver.commands.keys())
        stopwords.update([name, name.lower()])

        # Get tux outline image
        module_path = Path(__file__).parent.absolute()
        tux_path = module_path / "resources" / "tux.png"
        mask = np.array(Image.open(str(tux_path)))

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
        res = upload(file_and_path)

        os.remove(file_and_path)

        msg = "Cloud generated for " + name + ": "
        msg += res['link']
        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class TimeCommand(Command):

    @property
    def help_text(self) -> str:
        return "show the time"

    def execute(self, args: List[str]) -> bool:
        self._sender.send_privmsg(str(time.time()), self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class DateCommand(Command):

    @property
    def help_text(self) -> str:
        return "show the date"

    def execute(self, args: List[str]) -> bool:
        date_str = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc).isoformat(' ')
        self._sender.send_privmsg(date_str, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class WeekdayCommand(Command):

    @property
    def help_text(self) -> str:
        return "show the weekday"

    def execute(self, args: List[str]) -> bool:
        datetime.datetime.today().weekday()
        msg = calendar.day_name[datetime.datetime.today().weekday()]
        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class UptimeCommand(Command):

    @property
    def help_text(self) -> str:
        return "show my age"

    def execute(self, args: List[str]) -> bool:
        time_now = time.time()
        diff_sec = time_now - self._receiver.creation_time
        diff_time = datetime.timedelta(seconds=int(diff_sec))
        self._sender.send_privmsg(str(diff_time), self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class UpdogCommand(Command):

    @property
    def help_text(self) -> str:
        return "is it me or does it smell like updog in here"

    def execute(self, args: List[str]) -> bool:
        msg = "Nothing much, what's up with you?"
        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class InterjectCommand(Command):

    @property
    def help_text(self) -> str:
        return "set people right about GNU/Linux"

    def execute(self, args: List[str]) -> bool:
        msg = self._receiver.triggers[' linux'][1]
        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class CopypastaCommand(Command):

    @property
    def help_text(self) -> str:
        return "<query> get copypasta based on query"

    def execute(self, args: List[str]) -> bool:
        incoming_message = args[1]
        query = Command.check_arg(incoming_message)
        if not query:
            self._sender.send_privmsg('I need a search term.',
                                      self._receiver.channel,
                                      self._receiver.max_message_length)
            return False

        pasta = cps.get_copypasta(query)
        pasta = pasta[:self._receiver.max_message_length - 3]
        pasta = pasta.replace('\n', ' ')
        pasta = ' '.join(pasta.split())
        pasta = pasta.strip()
        pasta += '...'
        self._sender.send_privmsg(pasta, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True


class ShrugCommand(Command):

    @property
    def help_text(self) -> str:
        return "make the bot shrug"

    def execute(self, args: List[str]) -> bool:
        msg = r"¯\_(ツ)_/¯"
        self._sender.send_privmsg(msg, self._receiver.channel,
                                  self._receiver.max_message_length)
        return True
