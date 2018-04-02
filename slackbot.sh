#!/bin/bash
until slackbot.py; do
    echo "'slackbot.py' crashed with exit code $?. Restarting..." >&2
    sleep 1
done
