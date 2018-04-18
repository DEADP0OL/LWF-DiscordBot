#!/usr/bin/env bash
until ./lwfmain-bot.py; do
	echo "'lwfmain-bot.py' crashed with exit code $?. Restarting..." >&2
	sleep 1
done
