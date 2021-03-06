"""
    Simple Python module to store queried web page localy to retrieve them faster.

    The cached files are stored in a given directory and name with their md5 hash.
    Their creation date is stored in the same directory in a JSON file.
"""

import hashlib
import json
import getopt
import sys
from os import makedirs
from os.path import isfile, isdir
from datetime import datetime, timedelta
import requests
import io
from urllib.parse import urlparse

#  Will update the file from the server if the cached file is older than the limit.
timelimit = timedelta(days=7)

try:
    opts, args = getopt.getopt(sys.argv[1:], "vr", ["print"])
except getopt.GetoptError:
    print ('localPageCache.py')
    sys.exit(2)

verbose = False
for opt, arg in opts:
    if opt == '-v':
        verbose = True
    if opt == '-r':
        timelimit = timedelta(days=0)


_cacheDir = "pythonWebCache/"
_cacheDataFilePath = _cacheDir + "cacheData.json"


if isfile(_cacheDataFilePath):
    file = open(_cacheDataFilePath, "r")
    s = file.read()
    _cacheData = json.loads(s)
else:
    _cacheData = dict()


def getFileName(url):
    return _urlHash(url)


def getPage(url,infinite=False):
    """
    This is the only public function. Just call it the retrieve the page either from the web or from the cache
    The origin is determined by the module itself.
    """
    md5hash = _urlHash(url)

    if not isdir(_cacheDir):
        makedirs(_cacheDir)

    dirName = _cacheDir+''.join(urlparse(url).netloc.split('.')[:-1])+"/"

    if not isdir(dirName):
        makedirs(dirName)

    filename = dirName + md5hash

    if isfile(filename) and not _needsUpdate(url):
        if verbose:
            print("Loading page", url, "from cache")
        file = open(filename, "r")
        s = file.read()

        # if the cache is empty, try to redownload it
        if len(s) > 0:
            return s

    if verbose:
        print("Loading page", url, "from the web")
    try:
        r = requests.get(url)
        r.encoding = 'utf-8'
    except requests.exceptions.RequestException as e:
        print(str(e) + ' -- ' + url)
        return ""
    s = r.text

    file = io.open(filename, 'w', encoding='utf8')
    file.write(s)
    file.close()
    _setUpdateTime(url, infinite)
    return s
    return  # never reached


"""
    Return a md5 hash for an url (or any other string)
"""


def _urlHash(url):
    h = hashlib.md5()
    h.update(url.encode('utf-8'))
    return h.hexdigest()

"""
    sets the new creation time of a cached url and updates the cacheData json
"""


def _setUpdateTime(url,infinite):
    hash = _urlHash(url)

    # storing as a string since datetime is not serializable
    if infinite:
        _cacheData[hash] = "infinite"
    else:
        _cacheData[hash] = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Saving the data
    jsonData = json.dumps(_cacheData, indent=2, sort_keys=True)
    text_file = open(_cacheDataFilePath, "w")
    text_file.write(jsonData)
    text_file.close()

"""
    retrieves from the cacheData the creation time of the cached url
"""


def _updateTime(url):
    hash = _urlHash(url)
    if hash in _cacheData:
        # The date is stored as a text, it need to be parsed to be a datetime
        if _cacheData[hash] == "infinite":
            return None
        return datetime.strptime(_cacheData[hash], "%Y-%m-%d %H:%M:%S")
    else:
        return None

"""
    Computes if the cache needs to be updated for the given url
"""


def _needsUpdate(url):
    now = datetime.now()
    then = _updateTime(url)
    if then is not None:
        return (now - then) > timelimit
    else:
        return False
