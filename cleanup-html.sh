#!/bin/bash
sed -i 's/<script.*<\/script>//g' "$@"
sed -i -E 's/<!-- [A-Z]+ [0-9a-f]+-[A-Z]{3} :-->//g' "$@"
