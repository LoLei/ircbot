# ircbot
~~Small~~ bloated IRC bot :robot:

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

## Deployment
The bot can either be run from the git repo itself, as a container with e.g. docker or docker-compose, or within Kubernetes.  
It has been deployed for a long time (> 1 year) on a Raspberry Pi (therefore it works on ARM, which is made sure by some version requirements),
and it is currently deployed on Kubernetes. (See [`k8s/`](https://github.com/LoLei/ircbot/tree/master/k8s))

## Example User Word Cloud
<p align="center">
  <img width="500" height="500" src="https://raw.githubusercontent.com/LoLei/ircbot/master/images/wctux.png">
</p>
