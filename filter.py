#!/usr/bin/python3

import re
from lxml.html import fromstring
import json

with open("name_mapping.json") as _file:
	nameMapping = json.load(_file)


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
		m = re.match(
			"(\[.*\] )?(.*) - ([0-9]+|S[0-9][0-9]E[0-9][0-9])"
			" [- ]*[\\(\\[]?([0-9]+p)?[\\)\\]]?([^.]*)\.([a-zA-Z]+)",
			title,
		)
		if m is None:
			print(f"bad title: {title!r}")
			continue
		groups = m.groups()
		sub = groups[0].strip("[] ") if groups[0] else ""
		name = groups[1]
		ep = groups[2]
		res = groups[3]
		extra = groups[4]
		_format = groups[5]
		if ep.startswith("S01E"):
			ep = ep[len("S01E"):]
		if name in nameMapping:
			name = nameMapping[name]
		result.append({
			"title": title,
			"sub": sub,
			"name": name,
			"ep": ep,
			"res": res,
			"extra": extra,
			"format": _format,
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


def filterOutWatched(items, watched):
	result = []
	for item in items:
		name = item["name"]
		ep = item["ep"]
		if name not in watched:
			result.append(item)
			continue
		watchedEp = watched[name]
		if watchedEp is None:
			continue
		if ep > watchedEp:
			result.append(item)
			continue
	return result


def formatEpisodeSet(epSet):
	if len(epSet) == 1:
		return epSet.pop()
	epList = sorted(epSet)
	return epList[0] + ".." + epList[-1]


def getEpisodesByName(items):
	byName = {}
	for item in items:
		name = item["name"]
		ep = item["ep"]
		if name not in byName:
			byName[name] = set([ep])
			continue
		byName[name].add(ep)
	return byName


def main():
	with open("top.html") as fp:
		htmlStr = fp.read()
	items = parsePage(htmlStr)
	# print(json.dumps(items, indent="    "))

	watched = parseWatchedFile("watched.txt")
	# print(json.dumps(watched, indent="    "))

	items = filterOutWatched(items, watched)
	byName = getEpisodesByName(items)

	for name, epSet in sorted(byName.items()):
		epListStr = formatEpisodeSet(epSet)
		print(f"{name} - {epListStr}")


if __name__=="__main__":
	main()
