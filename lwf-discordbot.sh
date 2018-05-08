#!/usr/bin/env bash
until ./lwf-discordbot.py; do
	echo "'lwf-discordbot.py' crashed with exit code $?. Restarting..." >&2
	sleep 1
done
