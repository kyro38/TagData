#!/bin/env python

import sys
import getopt
import json
import localPageCache
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import difflib
import unicodedata
from pprint import pprint

try:
    opts, args = getopt.getopt(sys.argv[1:], "v", ["print"])
except getopt.GetoptError:
    print('getopt error in mobitrans.py')
    sys.exit(2)

verbose = False
for opt, arg in opts:
    if opt == '-v':
        verbose = True


"""
     Returns the mobitrans line ID for a given line name
"""


def idForLine(lineName):
    res = [x for x in _lineIds if x["name"] == lineName]
    res2 = [x for x in _lineIds if x["name"] == alternateName(lineName)]
    if res:
        return res[0]["lineID"]
    elif res2:
        return res2[0]["lineID"]
    else:
        names = [x["name"] for x in _lineIds]

        res = difflib.get_close_matches(lineName, names)
        if res and len(res[0]) > 1:  # Avoiding false positive with digit line numbers
            return [x for x in _lineIds if x["name"] == res[0]][0]["lineID"]

        res = difflib.get_close_matches(alternateName(lineName), names)
        if res and len(res[0]) > 1:  # Avoiding false positive with digit line numbers
            return [x for x in _lineIds if x["name"] == res[0]][0]["lineID"]

        # At this point we are desperate and return None found :(
        return None


"""
    As OSM Names & Mobitrans names sometimes don't match here are some alternate names
    The function OSM => Mobitrans
"""


def alternateName(aLineName):
    if 'Ebus' in aLineName:
        return 'EBUS'
    if 'Chrono' in aLineName:
        return 'C' + aLineName[-1]
    if 'Flexo' in aLineName:
        return aLineName[-2:]
    if 'Proximo' in aLineName:
        return aLineName[-2:]
    if 'Tram' in aLineName:
        return aLineName[-1]
    else:
        return list()


"""
     Find the line id on the mobitrans site
     Returns list of dict {MobitransId, name}
"""


def findLineIds():
    url = "http://tag.mobitrans.fr/horaires/index.asp?rub_code=23&keywords=e"
#    f = urlopen(url)
#    s = f.read()
    s = localPageCache.getPage(url)
    soup = BeautifulSoup(s)
    rubDiv = soup.find("div", class_="rub_content")

    ulLignes = rubDiv.find("ul", class_="lig")
    lignes = ulLignes.findAll("li", recursive=False)
    lines = list()


    for ligne in lignes:

        if ligne.find("img") is not None and len(ligne.findAll("img")) is 2:
                name = ligne.findAll("img")[1]['alt']

                aLine = dict()
                aLine['name'] = name
                url = ligne.find("a").attrs['href']
                parsed = parse_qs(urlparse(url).query, keep_blank_values=True)
                aLine['lineID'] = int(parsed["lign_id"][0])
                lines.append(aLine)
        elif ligne.find("img") is not None and len(ligne.findAll("img")) is 1 :
            name = ligne.find('span').text

            aLine = dict()
            aLine['name'] = name
            url = ligne.find("a").attrs['href']
            parsed = parse_qs(urlparse(url).query, keep_blank_values=True)
            aLine['lineID'] = int(parsed["lign_id"][0])
            lines.append(aLine)
        else :
            print('PROBLEM')

    if(verbose):
        print(json.dumps(lines, indent=4, sort_keys=True))

    return lines


"""
     For a stationName (for example provided by OSM)
     It queries Mobitrans to find a matching name and returns its Id for the given direction
"""


def stationIdForLine(name, lineId, sens):
    stations = stationsForLine(lineId, sens)
    stationNameList = [x["name"] for x in stations]

    result = difflib.get_close_matches(name, stationNameList)
    if not result:
        result = [s for s in stationNameList if s in name]
    if not result:
        asciiName = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        result = [s for s in stationNameList if s in asciiName]
        if not result:
            result = result = [s for s in stationNameList if asciiName in s]

    if not result:
        # Assuming the station is not available on Mobitrans for that direction
        # Keeping the ouput to remind to correct OSM.
        print(name, "id:", lineId, "sens:", sens, " - Station not available on Mobitrans for that direction")
        print(stationNameList)

        return None
    theStation = [x for x in stations if x["name"] == result[0]]
    if len(theStation) > 0:
        return theStation[0]['stationID']
    else:
        print("Can't find the station return by the difflib")
        return None

"""
     For a line and a direction it return a ordered list of dict {name, mobitransStationID} for the given direction
     The info are retrieved from mobitrans
"""


def stationsForLine(lineID, sens):
    # Caching the webpages to only retrieve them once from the web
    if str(lineID) in _mbtStations and "sens" + str(sens) in _mbtStations[str(lineID)]:
        return _mbtStations[str(lineID)]["sens" + str(sens)]

    else:
        url = "http://tag.mobitrans.fr/horaires/index.asp?rub_code=23&typeSearch=line&lign_id=" + str(lineID) + "&sens=" + str(sens)
        s = localPageCache.getPage(url)

        #Using BeautifulSoup to parse the DOM
        soup = BeautifulSoup(s)
        rubDiv = soup.find("div", class_="rub_content")

        ulStops = rubDiv.find("ul", class_="stops")
        if(not ulStops):
            return list()

        stops = ulStops.findAll("li", recursive=False)

        lineStops = list()

        for aStop in stops:
            theStop = dict()
            theStop['name'] = aStop.next.string
            url = aStop.find("a").attrs['href']
            parsed = parse_qs(urlparse(url).query, keep_blank_values=True)
            theStop['stationID'] = int(parsed["pa_id"][0])
            lineStops.append(theStop)

                # stationDict = dict()
                # stationDict['sens'] = sens
                # stationDict['stations'] = lineStops
        if str(lineID) not in _mbtStations:
            _mbtStations[str(lineID)] = dict()

        _mbtStations[str(lineID)]["sens" + str(sens)] = lineStops
        return lineStops

_lineIds = findLineIds()
# pprint(_lineIds)
_mbtStations = dict()
