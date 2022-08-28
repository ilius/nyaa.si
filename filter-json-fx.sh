#!/bin/bash

(
	echo "["
	last_line=

	# with: some_command | while read -r line ; do ...
	# a sub-shell is created to run the while loop,
	# so the last_line variable is isolated in that sub-shell
	# and becomes inaccessible outside the loop

	while read -r line ; do
		if [ -z "$line" ] ; then
			continue
		fi
		if [ -n "$last_line" ] ; then
			echo "$last_line,"
		fi
		last_line=$line
	done < <(./filter.py --json "$@")

	echo "$last_line"
	echo "]"

) | fx
