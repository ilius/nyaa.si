#!/bin/bash

./filter.py --json | jq -C . --tab | less -R "$@"

