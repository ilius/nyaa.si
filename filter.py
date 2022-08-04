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


subReS = "(?P<sub>\[[^\[\]]+\] )?"

resReS = "(" + "|".join([
	"(?P<res>[\\(\\[]([A-Z ]*?[0-9]+p[A-Z ]*?)[\\)\\]])",
	"(?P<res2>[0-9]+p)",
	"(?P<res3>\([^()]*?[0-9]+x[0-9]+[^()]*?)",
]) + ")?"

ignorePostEpSuffix = "(END )?(\[?Uncensored\]? )?"

episodeTitleRE = [
	re.compile(
		subReS +
		"(?P<name>[^0-9()]+( S[0-9]+)?) - "
		"(?P<ep>[0-9]+ |S[0-9][0-9]E[0-9][0-9] )?" +
		ignorePostEpSuffix +
		"[- ]*" +
		resReS +
		"(?P<extra>.*)",
	),
	re.compile(
		subReS +
		"(?P<name>[^0-9()]+ \\([^()]+\\)) - "
		"(?P<ep>[0-9]+ |S[0-9][0-9]E[0-9][0-9] )?" +
		ignorePostEpSuffix +
		"[- ]*" +
		resReS +
		"(?P<extra>.*)",
	),
	re.compile(
		subReS +
		"(?P<name>[^0-9()]+) "
		"(?P<ep>S[0-9][0-9]E[0-9][0-9] )"
		"[- ]*" +
		ignorePostEpSuffix +
		resReS +
		"(?P<extra>.*)",
	),
	re.compile(
		subReS +
		"(?P<name>[^\[\]]+) " +
		resReS +
		"(?P<extra>.*)",
	),
]

nameSeasonRE = re.compile("(.*) (S[0-9]+)")




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
		m = None
		for pattern in episodeTitleRE:
			m = pattern.match(title)
			if m is not None:
				break
		else:
			error(f"bad title", title=title)
			continue
		groups = m.groupdict()
		sub = groups["sub"].strip("[] ") if groups["sub"] else ""
		name = groups["name"].strip(" -!")
		ep = groups.get("ep", "")

		res = "unknown"
		for key in ("res", "res2", "res3"):
			if groups[key]:
				res = groups[key].strip("[]()")
				break

		#if res == "unknown":
		#	error("unknown res", title=title, groups=groups)

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
			"sub": set([sub]),
			"name": name,
			"name_tr": nameTranslation.get(name, ""),
			"ep": ep,
			"res": set([res]),
			"extra": extra,
			"time_formatted": timeStr,
			"timestamp": timestamp,
		}
		# row["groups"] = groups
		result.append(row)

	return result

def parseWatchedFile(fname):
	result = {}  # Dict[str, Optional[str]]
	comments = {}  # Dict[str, str]
	with open(fname) as _file:
		for line in _file:
			if line.startswith("#"):
				continue
			line, _, comment = line.partition("#")
			line = line.strip()
			comment = comment.strip()
			if not line:
				continue
			parts = [
				part
				for part in line.split("\t")
				if part
			]
			if len(parts) == 0:
				continue
			name = parts[0]
			if comment:
				comments[name] = comment
			if len(parts) == 1:
				result[name] = None
				continue
			if len(parts) != 2:
				error("bad line", line=line)
				continue
			epRange = parts[1].lstrip("\t")
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
	return result, comments


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


def organizeByName(items):
	byName = {}
	for item in items:
		name = item["name"]
		ep = item["ep"]

		if name not in byName:
			byName[name] = (item, set([ep]))
			continue

		item0 = byName[name][0]
		if item0["ep"] == ep:
			item0["sub"].update(item["sub"])
			item0["res"].update(item["res"])
			item0["extra"] = "\n".join([
				x["extra"]
				for x in (item0, item)
				if x["extra"]
			])

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
		watched, comments = parseWatchedFile(watchedFilePath)
	else:
		watched, comments = {}, {}
	# print(json.dumps(watched, indent="    "))

	if "--all" not in sys.argv[1:]:
		items = filterOutWatched(items, watched)

	byName = organizeByName(items)

	for name, (item, epSet) in sorted(byName.items()):
		epListStr = formatEpisodeSet(epSet)
		time_formatted = item["time_formatted"]

		subList = list(sorted(item["sub"]))
		subStr = " | ".join(subList)
		item["sub"] = subStr
		sub = subStr

		resList = list(sorted(item["res"]))
		resStr = " | ".join(resList)
		item["res"] = resStr

		name_tr = item["name_tr"]
		comment = comments.get(name, "")
		if comment == name_tr:
			comment = ""
		if comment:
			item["comment"] = comment
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
