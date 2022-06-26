#!/bin/bash

./filter.py --json 2>&1 | jq -C . --tab | less -R

