URL='https://nyaa.iss.ink/?s=seeders&o=desc'
DTIME=$(date +%Y-%m-%d-%H%M%S)

if ! wget -O "top-$DTIME.html" "$URL" ; then
	rm "top-$DTIME.html"
	exit 1
fi

ln -sf "top-$DTIME.html" top.html

./filter-json-pretty.sh > top.json
