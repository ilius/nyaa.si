#!/bin/bash

./filter.py --json 2>&1 | jq -cC .  | less -R -S