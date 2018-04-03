#!/usr/bin/env bash
until python3 slackbot.py; do
    echo "'slackbot.py' crashed with exit code $?. Restarting..." >&2
    sleep 1
done
