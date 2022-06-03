#!/usr/bin/python3

# URL: https://nyaa.si/?s=seeders&o=desc

import re
from lxml.html import fromstring

# "[SubsPlease] Tomodachi Game - 09 (1080p) [BFD8B19A].mkv"
# {"sub": "SubsPlease", "name": "Tomodachi Game",
#  "ep": "09", "res": "1080p", "extra": " [BFD8B19A]", format: "mkv"}
def parsePage(htmlStr: str) -> "List[Dict[str, str]]":
	tree = fromstring(htmlStr)
	result = []
	for a in tree.xpath("//td/a"):
		href = a.attrib["href"]
		if not href.startswith("/view/"):
			continue
		idStr = href[len("/view/"):]
		try:
			idInt = int(idStr)
		except ValueError:
			continue
		title = a.attrib["title"]
		# m = re.match("\[(.*)\] (.*) - ([0-9]+) \(([0-9]+p)\)([^.]*)\.([a-zA-Z]+)", title)
		m = re.match("(\[.*\] )?(.*) - ([0-9]+|S[0-9][0-9]E[0-9][0-9]) [- ]*[\\(\\[]?([0-9]+p)?[\\)\\]]?([^.]*)\.([a-zA-Z]+)", title)
		if m is None:
			print(f"bad title: {title!r}")
			continue
		#bad title: '[Ohys-Raws] Gaikotsu Kishi-sama, Tadaima Isekai e Odekake-chuu - 09 (AT-X 1280x720 x264 AAC).mp4'
		#bad title: '[SlyFox] Summertime Rendering (Summer Time Render) - 07 [297E6E53].mkv
		groups = m.groups()
		result.append({
			"title": title,
			"sub": groups[0].strip("[] ") if groups[0] else "",
			"name": groups[1],
			"ep": groups[2],
			"res": groups[3],
			"extra": groups[4],
			"format": groups[5]
		})
	return result

def parseWatchedFile(fname):
	result = {}  # Dict[str, Optional[str]]
	with open(fname) as _file:
		for line in _file:
			parts = line.strip().split("\t")
			if len(parts) == 0:
				continue
			name = parts[0]
			if len(parts) == 1:
				result[name] = None
				continue
			if len(parts) != 2:
				print(f"bad line: {line}")
				continue
			epRange = parts[1]
			if epRange.startswith(".."):
				end = epRange[2:].lstrip("E")
				result[name] = end
				continue
			if ".." in epRange:
				startStr, endStr = epRange.split("..")
				end = endStr.lstrip("E")
				result[name] = end
				continue
			print(f"bad line: {line}")
	return result



if __name__=="__main__":
	with open("top.html") as fp:
		htmlStr = fp.read()
	items = parsePage(htmlStr)

	watched = parseWatchedFile("watched.txt")

	#from pprint import pprint ; pprint(watched)

	for item in items:
		name = item["name"]
		ep = item["ep"]
		if name not in watched:
			print(f"{name} - {ep}")
			continue
		watchedEp = watched[name]
		if watchedEp is None:
			continue
		if ep > watchedEp:
			print(f"{name} - {ep}")
			continue



	# from json import dumps
	# print(dumps(allEpisodes, indent="    "))


