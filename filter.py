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
	"(?P<sub>\[.*\] )?"
	"(?P<name>[^0-9]*( S[0-9]+)?) - "
	"(?P<ep>[0-9]+ |S[0-9][0-9]E[0-9][0-9] )?"
	"(END )?"
	"[- ]*"
	"[\\(\\[]?"
	"(?P<res>[0-9]+p)?"
	"[\\)\\]]?"
	"(?P<extra>.*)",
)
nameSeasonRE = re.compile("(.*) (S[0-9]+)")

# TODO: replace episodeTitleRE with a list of expressions with named groups


def errorJson(msg, data, **kwargs):
	data["error"] = msg
	print(
		json.dumps(
			data,
			ensure_ascii=False,
			**kwargs
		),
		file=sys.stderr,
	)


def error(msg, **data):
	if outMode == "json":
		errorJson(msg, data)
		return
	if outMode == "json-pretty":
		errorJson(msg, data, indent="    ")
		return
	valuesStr = ", ".join([repr(x) for x in data.values()])
	print(f"--- {msg}: {valuesStr}", file=sys.stderr)


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
			error(f"bad title", title=title)
			continue
		groups = m.groupdict()
		sub = groups["sub"].strip("[] ") if groups["sub"] else ""
		name = groups["name"].strip(" -")
		ep = groups["ep"]
		res = groups["res"]
		extra = groups["extra"].strip()
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

		row = {
			"title": title,
			"sub": sub,
			"name": name,
			"name_tr": nameTranslation.get(name, ""),
			"ep": ep,
			"res": res,
			"extra": extra,
			"time_formatted": timeStr,
			"timestamp": timestamp,
		}
		# row["groups"] = groups
		result.append(row)

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
				error("bad line", line=line)
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
			error(f"bad line", line=line)
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


# TODO: read a list of regex patterns from ignore.txt


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


def formatTranslateName(item):
	name = item["name"]
	nameTr = item["name_tr"]
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
		time_formatted = item["time_formatted"]
		sub = item["sub"]
		if outMode == "json":
			print(json.dumps(item, ensure_ascii=False))
		elif outMode == "json-pretty":
			print(json.dumps(item, ensure_ascii=False, indent="    "))
		else:
			name = formatTranslateName(item)
			# print(f"{time_formatted} [{sub}] {name} - {epListStr}")
			print(f"[{sub}] {name} - {epListStr}")


if __name__=="__main__":
	main()
