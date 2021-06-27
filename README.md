# ircbot
~Small~ bloated IRC bot :robot:

Tested with [irc.snoonet.org](https://snoonet.org/)

## Features
* Automatic reconnect on connection loss
* Live injection of new responses at runtime
* Persistent user database
* Variable command prefix
* Easy new command addition
  * As simple as creating a new subclass in `command.py`
* Many built-in commands
* Dynamic overly-long message splitting (Thanks primitve IRC protocol)

## Usage
Start it once on your server and use the commands within your IRC client.  

### Server
```
./start.py
```
Configure settings (nick, server, channel, command prefix, etc.) in `.env`.  
(This file isn't read but the environment variables must be set. Source them via e.g. `export $(cat .env | xargs)`.)

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

## Container
```sh
# Prepare
docker pull ghcr.io/lolei/ircbot:<tag>
# or
docker build -f Containerfile . -t ghcr.io/lolei/ircbot:<tag>

# Run
docker run --env-file .env.local -v $(pwd)/storage:/app/storage ghcr.io/lolei/ircbot:<tag>
```

## Example User Word Cloud
<p align="center">
  <img width="500" height="500" src="https://raw.githubusercontent.com/LoLei/ircbot/master/images/wctux.png">
</p>
