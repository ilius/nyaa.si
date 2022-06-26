#!/usr/bin/python3

import re
import os
import sys
from lxml.html import fromstring
import json
from os.path import isfile
from datetime import datetime



with open("name_mapping.json") as _file:
	nameMapping = json.load(_file)

with open("name_english.json") as _file:
	nameTranslation = json.load(_file)


outMode = ""
if "--json" in sys.argv:
	outMode = "json"
elif "--json-pretty" in sys.argv:
	outMode = "json-pretty"


episodeTitleRE = re.compile(
	"(\[.*\] )?([^0-9]*?( S[0-9]+)? - )([0-9]+|S[0-9][0-9]E[0-9][0-9] )?"
	"[- ]*[\\(\\[]?([0-9]+p)?[\\)\\]]?(.*)",
)
nameSeasonRE = re.compile("(.*) (S[0-9]+)")

# TODO: replace episodeTitleRE with a list of expressions with named groups

def error(msg):
	if outMode == "json":
		print(
			json.dumps(
				{"error": msg},
				ensure_ascii=False,
			),
			file=sys.stderr,
		)
		return
	if outMode == "json-pretty":
		print(
			json.dumps(
				{"error": msg},
				ensure_ascii=False,
				indent="    ",
			),
			file=sys.stderr,
		)
		return
	print(f"--- {msg}", file=sys.stderr)


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
		m = episodeTitleRE.match(title)
		if m is None:
			error(f"bad title: {title}")
			continue
		groups = m.groups()
		sub = groups[0].strip("[] ") if groups[0] else ""
		name = groups[1].strip(" -")
		ep = groups[3]
		res = groups[4]
		extra = groups[5].strip()
		if ep:
			ep = ep.strip()
			if ep.startswith("S01E"):
				ep = ep[len("S01E"):]
		else:
			ep = "00"
		if name in nameMapping:
			name = nameMapping[name]

		tr = a.getparent().getparent()
		timeTd = tr.xpath('//td[@data-timestamp]')[0]
		timestamp = int(timeTd.attrib["data-timestamp"])
		# timeStr = timeTd.text  # in UTC
		timeStr = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')

		result.append({
			"title": title,
			"sub": sub,
			"name": name,
			"ep": ep,
			"res": res,
			"extra": extra,
			"time_formatted": timeStr,
			"timestamp": timestamp,
			"groups": groups,
		})
	return result

def parseWatchedFile(fname):
	result = {}  # Dict[str, Optional[str]]
	with open(fname) as _file:
		for line in _file:
			if line.startswith("#"):
				continue
			line = line.strip().split("#")[0]
			if not line:
				continue
			parts = line.split("\t")
			if len(parts) == 0:
				continue
			name = parts[0]
			if len(parts) == 1:
				result[name] = None
				continue
			if len(parts) != 2:
				error(f"bad line: {line}")
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
			error(f"bad line: {line}")
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
	if epList[0] == "01":
		return ".." + epList[-1]
	return epList[0] + ".." + epList[-1]


def getEpisodesByName(items):
	byName = {}
	for item in items:
		name = item["name"]
		ep = item["ep"]
		if name not in byName:
			byName[name] = (item, set([ep]))
			continue
		byName[name][1].add(ep)
	return byName


def formatTranslateName(name):
	nameTr = nameTranslation.get(name, "")
	if nameTr:
		return f"{name} ({nameTr})"

	m = nameSeasonRE.match(name)
	if m:
		nameNS = m.group(1)
		nameTr = nameTranslation.get(nameNS, "")
		if nameTr:
			season = m.group(2)
			return f"{nameNS} ({nameTr}) {season}"

	return name


def main():
	with open("top.html") as fp:
		htmlStr = fp.read()
	items = parsePage(htmlStr)
	# print(json.dumps(items, indent="    "))

	watchedFilePath = "watched.txt"
	if isfile(watchedFilePath):
		watched = parseWatchedFile(watchedFilePath)
	else:
		watched = {}
	# print(json.dumps(watched, indent="    "))

	items = filterOutWatched(items, watched)
	byName = getEpisodesByName(items)

	for name, (item, epSet) in sorted(byName.items()):
		epListStr = formatEpisodeSet(epSet)
		name = formatTranslateName(name)
		time_formatted = item["time_formatted"]
		sub = item["sub"]
		if outMode == "json":
			print(json.dumps(item, ensure_ascii=False))
		elif outMode == "json-pretty":
			print(json.dumps(item, ensure_ascii=False, indent="    "))
		else:
			# print(f"{time_formatted} [{sub}] {name} - {epListStr}")
			print(f"[{sub}] {name} - {epListStr}")


if __name__=="__main__":
	main()
