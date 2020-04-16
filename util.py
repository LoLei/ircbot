class User():
    def __init__(self, name, timestamp, msg):
        self.name_ = name
        self.last_seen_ = timestamp
        self.last_message_ = msg

    def __str__(self):
        return "{}\n{}\n{}\n".format(self.name_, self.last_seen_,
                                     self.last_message_)
