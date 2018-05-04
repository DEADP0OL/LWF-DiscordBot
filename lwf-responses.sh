#!/usr/bin/env bash
until ./lwf-responses.py; do
	echo "'lwf-responses.py' crashed with exit code $?. Restarting..." >&2
	sleep 1
done
