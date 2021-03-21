#!/usr/bin/env python3

from src.ircbotserver import main as server_main


def start_server() -> None:
    server_main()


if __name__ == "__main__":
    start_server()
