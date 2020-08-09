import requests
import random
from bs4 import BeautifulSoup

WIKI = "https://gbf.wiki/"
API = WIKI + "api.php"
USER_AGENT = "Granblue SA Silva Bot (Written by Hail Hydrate#9035)"

# Returns a dictionary mapping Mediawiki page IDs to weapon names
# TODO: only gets the first 500 right now, because of limitations
# either figure out paging or get bot permission to go up to 5000
def getIndex(session):
    q = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Weapons",
        "cmlimit": 2500,
        "format": "json",
    }
    res = session.get(url=API, params=q, headers={"User-Agent": USER_AGENT})
    items = res.json()["query"]["categorymembers"]
    return {i["pageid"]: i["title"] for i in items}


# Extracts the associated weapon's flavor text given a page ID
def weaponDescriptionFromId(session, id):
    q = {"curid": id}
    res = session.get(url=WIKI, params=q, headers={"User-Agent": USER_AGENT})
    soup = BeautifulSoup(res.text, "html.parser")
    m = soup.find("div", attrs={"class": "weapon"}).find_all("table")
    for table in m:
        elements = table.find_all("tr")
        if "display:none;" in str(table) and len(elements) == 2:  # fuck it
            return elements[1].contents[1].string
    return None


# Selects a random weapon from a getIndex() result and returns a
# dictionary mapping the weapon's name with its flavor text
def randomWeaponDescription(session, index):
    id = random.choice(list(index.keys()))
    return {index[id]: weaponDescriptionFromId(session, id)}
