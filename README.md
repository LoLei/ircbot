# ircbot
Smol IRC bot :robot:

Tested with [irc.snoonet.org](https://snoonet.org/)

## Features
* Automatic reconnect on connection loss
* Live injection of new responses at runtime
* Persistent user database
* Variable command prefix
* Easy new command addition
  * As simple as creating a new subclass in `command.py`

## Usage
Start it once on your server and use the commands within your IRC client.  
See an example in `ircbotclient.py`.

### Server
```
IRCPW='<password>' ./ircbotclient.py
```
<sup>Also API tokens for Imgur if the `ImageUploader` is to be used.</sup>

Set other settings (nick, server, channel, command prefix, etc.) in `ircbotclient.py` itself.

### Client
```
\help
\cmds
\about
\uptime
\date
\time
\sentiment <text>|<user>
\lastmessage <user>
\words <user>
\wordcloud <user>
...
```
Only the last 1000 messages of users are stored. This parameter can be changed.

## Installation
```
git clone https://github.com/LoLei/ircbot ~/git/ircbot
```

## Coming Improvements
* Config file for many of the constructor parameters and environment variables.
