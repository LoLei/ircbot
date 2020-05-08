from sklearn.feature_extraction import text
from wordcloud import STOPWORDS

stopwords = set()

# stop words from sklearn
stopwords = stopwords.union(text.ENGLISH_STOP_WORDS)

# stop words from wordcloud
stopwords = STOPWORDS.union(stopwords)

# custom stopwords
# from config and/or bot commands
stopwords.update(['http', 'https'])

# Adapt for how wordcloud and sklearn CountVectorizer handle stop words
# Satisfy both
preprocessed_stopwords = []
for sw in stopwords:
    if '\'' not in sw:
        continue
    parts = sw.split('\'')
    preprocessed_stopwords.append(parts[0])
    preprocessed_stopwords.append(parts[1])

stopwords.update(preprocessed_stopwords)
