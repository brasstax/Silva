#!/usr/bin/env python

import pytz
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup, element
from copy import copy
from typing import List, Dict


async def init_wiki():
    """
    Async-creates the wiki object and sets its .soup to actual JSON.
    return: gbfwiki.wiki wiki
    """
    wiki = Wiki()
    await wiki._init()
    return wiki


class Wiki:
    def __init__(self):
        self.base_url = "https://gbf.wiki"
        self.url = f"{self.base_url}/api.php"
        self.headers = {
            "User-Agent": "Granblue SA Silva Bot (Written by Hail Hydrate#9035)",
            "Accept": "application/json",
        }

    async def _init(self):
        self.soup = await self.get_main_page()
        self.main_page_special = await self.get_main_page_special()

    async def get_main_page(self):
        params: dict = {
            "action": "cargoquery",
            "format": "json",
            "tables": "event_history",
            "fields": "name, utc_end, utc_start, time_start, time_end, element,"
            " wiki_page",
            "where": "(time_start >= NOW()) OR time_end >= NOW()",
        }
        headers = self.headers
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self.url, params=params, headers=headers
                ) as resp:
                    text = await resp.json()
            except Exception as e:
                raise (self.UnreachableWikiError(e))
        json_output = text["cargoquery"]
        return json_output

    async def get_main_page_special(self):
        """
        Retrieves the Special section of the main page.
        """
        params: dict = {
            "action": "parse",
            "format": "json",
            "page": "Template:MainPageSpecial",
            "prop": "text",
        }
        headers = self.headers
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self.url, params=params, headers=headers
                ) as resp:
                    text = await resp.json()
            except Exception as e:
                raise (self.UnreachableWikiError(e))
        text_output = text["parse"]["text"]["*"]
        html_output = BeautifulSoup(text_output, "html.parser")
        return html_output

    def get_events(self):
        """
        Scrapes the soup for events and sorts them into upcoming and
        current events.
        return: dict events
        """
        soup: dict = self.soup
        events: dict = {"upcoming": [], "current": []}
        now: datetime.datetime = datetime.utcnow().replace(tzinfo=pytz.utc)
        for span in soup:
            event: dict = {}
            event["title"] = span["title"]["name"]
            event["start"] = span["title"]["time start"]
            if span["title"]["time end"] != "":
                event["finish"] = span["title"]["time end"]
            else:
                event["finish"] = "¯\_(ツ)_/¯"  # noqa
            event["utc start"] = int(span["title"]["utc start"])
            event["utc end"] = int(span["title"]["utc end"])
            if span["title"]["element"] != "":
                event["title"] += f" ({span['title']['element']})"
            if span["title"]["wiki page"] != "":
                url = f"{self.base_url}/{span['title']['wiki page']}".replace(" ", "_")
                event["url"] = url
            else:
                event["url"] = "No wiki page"
            if datetime.fromtimestamp(int(span["title"]["utc start"]), pytz.utc) <= now:
                events["current"].append(event)
            else:
                events["upcoming"].append(event)
        special_events = self.get_special_events()
        for event in special_events:
            start = datetime.fromtimestamp(event["utc start"], pytz.utc)
            end = datetime.fromtimestamp(event["utc end"], pytz.utc)
            if start <= now:
                if end > now:
                    events["current"].append(event)
            else:
                events["upcoming"].append(event)
        events["current"] = sorted(events["current"], key=lambda k: k["utc start"])
        events["upcoming"] = sorted(events["upcoming"], key=lambda k: k["utc start"])
        return events

    def get_special_events(self) -> List[element.Tag]:
        soup = self.main_page_special
        events: list = []
        for span in soup.find_all("span", {"data-text-after": "Event has ended."}):
            event: dict = {}
            event["title"] = span.parent.parent.a["title"]
            event["utc start"]: int = int(span["data-start"])
            event["utc end"]: int = int(span["data-end"])
            # Change the output of the start and end text date to match the
            # output of the rest of the event date text.
            start = datetime.utcfromtimestamp(event["utc start"]).replace(
                tzinfo=pytz.utc
            )
            start = start.astimezone(tz=pytz.timezone("Asia/Tokyo"))
            end = datetime.utcfromtimestamp(event["utc end"]).replace(tzinfo=pytz.utc)
            end = end.astimezone(tz=pytz.timezone("Asia/Tokyo"))
            event["start"] = datetime.strftime(start, "%Y-%m-%d %H:%M JST")
            event["finish"] = datetime.strftime(end, "%Y-%m-%d %H:%M JST")
            event["url"] = f"{self.base_url}{span.parent.parent.a['href']}"
            events.append(event)
        return events

    async def _get_wikimedia_query_api(self, cmpageid: int) -> Dict[str, str]:
        """ Gets full list of category members based on numeric cmpageid
        input. Requests for maximum number of entries. Returns list of JSON
        of entries. """
        params = {
            "action": "query",
            "list": "categorymembers",
            "format": "json",
            "cmpageid": cmpageid,
            "cmtype": "page",
            "cmlimit": "max",
        }
        headers: dict = {
            "User-Agent": "Granblue SA Silva Bot (Written by Hail Hydrate#9035)",
            "Accept": "application/json",
        }
        url = self.url
        async with aiohttp.ClientSession() as session:
            async_res = await session.get(
                url, headers=headers, params=params, timeout=10
            )
        # The default return also returns batchcomplete information.
        # We don't care, so we only return the category's members.
        res = await async_res.json()
        return res["query"]["categorymembers"]

    async def get_summons_page(self):
        """
        Gets the summons page and removes the Summons List pages.
        """
        summons_full = await self._get_wikimedia_query_api(12225)
        summons = [
            summon for summon in summons_full if "Summons List" not in summon["title"]
        ]
        return summons

    async def get_page(self, pageid: int) -> Dict[str, str]:
        """
        Retrieves a page by page ID.
        """
        params = {"action": "parse", "pageid": pageid, "format": "json"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self.url, params=params, headers=self.headers
                ) as resp:
                    text = await resp.json()
            except Exception as e:
                raise (self.UnreachableWikiError(e))
            if "error" in text.keys():
                raise self.NoPageFound(f"Page {pageid} not found.")
        return text

    async def get_page_text(self, pageid: int, key: str = "*") -> str:
        """
        Gets page text from parsed results of a page.
        key: page['parse']['text'][key]. defaults to '*'.
        pageid: the page ID.
        returns the text.
        """
        page = await self.get_page(pageid)
        if "parse" not in page.keys():
            raise self.NoPageFound(f"Page ID {pageid} has no parsed results.")
        if "text" not in page["parse"].keys():
            raise self.NoPageFound(f"Page ID {pageid} has no parsable text.")
        if key not in page["parse"]["text"].keys():
            raise self.NoPageFound(f"Page ID {pageid} does not have the key {key}.")
        return page["parse"]["text"][key]

    async def get_page_soup(self, pageid: int, key: str = "*") -> BeautifulSoup:
        """
        Transforms the page text into a BeautifulSoup HTML object.
        key: page['parse']['text'][key]. defaults to '*'.
        pageid: the page ID.
        returns the text.
        """
        text = await self.get_page_text(pageid, key)
        soup = BeautifulSoup(text, "html.parser")
        return soup

    async def get_summon_name(self, page: BeautifulSoup) -> str:
        """
        Gets the name of a summon.
        """
        return page.find("div", {"class": "char-name"}).text

    async def get_summon_call(self, page: BeautifulSoup) -> str:
        """
        Gets the call name of a summon.
        """
        if not page.find("a", text="Call"):
            char_name = page.find("div", {"class": "char-name"}).text
            raise self.NoPageFound(f'Summon "{char_name})" has no call information.')
        call_full = page.find("a", text="Call").find_previous("th").text
        call = call_full.split("-")[1]
        return call.lstrip()

    async def get_summon_first_half(self, page: BeautifulSoup) -> str:
        """
        Gets the first half call name of a summon.
        """
        char_name = page.find("div", {"class": "char-name"}).text
        if not page.find(text="Combo Call Name"):
            raise self.NoPageFound(
                f'Summon "{char_name})" has no combo call information.'
            )
        if not page.find(text="First Half"):
            raise self.NoFirstHalfCombo(f'Summon "{char_name}" has no first half.')
        return page.find(text="First Half").find_next("td").text

    async def get_summon_second_half(self, page: BeautifulSoup) -> str:
        """
        Gets the second half call name of a summon.
        """
        char_name = page.find("div", {"class": "char-name"}).text
        if not page.find(text="Combo Call Name"):
            raise self.NoPageFound(
                f'Summon "{char_name})" has no combo call information.'
            )
        return page.find(text="Second Half").find_next("td").text

    async def get_combo_name(self, summon1: int, summon2: int) -> str:
        """
        Gets the combo call name of two summons.
        If a summon doesn't have a combo name recorded (Illuyanka),
        return one of the summons' call name.
        If the first summon doesn't have a first half (Arcarum summons),
        make it the second half.
        If both summons are uncrossable (no combo name or no first half),
        raise an uncrossable exception.
        summon1 and summon2 are the page IDs to search.
        Return the call name.
        """
        s1 = await self.get_page_soup(summon1)
        s2 = await self.get_page_soup(summon2)
        try:
            s1_first = await self.get_summon_first_half(s1)
        except (self.NoFirstHalfCombo, self.NoPageFound):
            s1_first = None
        try:
            s2_first = await self.get_summon_first_half(s2)
        except (self.NoFirstHalfCombo, self.NoPageFound):
            s2_first = None
        if not s1_first and not s2_first:
            raise self.UncrossableSummonsException
        try:
            s1_second = await self.get_summon_second_half(s1)
            s2_second = await self.get_summon_second_half(s2)
        except self.NoPageFound:
            raise self.UncrossableSummonsException
        if s1_first:
            return f"{s1_first} {s2_second}"
        else:
            return f"{s2_first} {s1_second}"

    def get_upcoming_events_html(self) -> List[element.Tag]:
        """
        Scrapes the soup for a elements to identify
        the upcoming events section.
        Deprecated since we can get JSON output, but remains in case it's
        needed for a future function.
        return: list events
        """
        soup: List(dict) = self.soup
        future_events = soup.find(
            text="Upcoming Events"
        ).parent.parent.next_sibling.next_sibling
        events = future_events.find_all("a")
        # Check to make sure the event is properly wrapped in a <p>
        for idx, event in enumerate(events):
            if not self.is_wrapped_event(event):
                e = self.wrap_around_p(event)
                events[idx] = e
            else:
                events[idx] = event.parent
        return events

    def get_upcoming_events_by_scraping(self) -> List[dict]:
        """
        Runs get_upcoming_events_html and returns a list of dictionaries.
        Deprecated since we can get JSON output, but remains in case it's
        needed for a future function.
        """
        html: List[element.Tag] = self.get_upcoming_events_html()
        events: list = []
        for p in html:
            event: dict = {}
            event["title"] = p.find("a")["title"]
            # Italicized special text will be added to the
            # title in parenthesis.
            if p.find("i"):
                event["title"] += f" ({p.find('i').text})"
            event["url"] = f"{self.base_url}{p.find('a')['href']}"
            # The duration is in the element after the last break.
            event["duration"] = str(p.find_all("br")[-1].next_sibling)
            # In case of duplicates, skip.
            if event not in events:
                events.append(event)
        return events

    def is_wrapped_event(self, event: element.Tag) -> bool:
        """
        Checks to see if an upcoming event is properly wrapped in a <p>
        HTML element.
        Deprecated since we can get JSON output, but remains in case it's
        needed for a future function.
        """
        return event.parent.name == "p"

    def wrap_around_p(self, event: element.Tag) -> element.Tag:
        """
        Wraps elements around a <p> tag until the function reaches the next <p>
        tag, or the end of the document.
        return clone: element.Tag
        """
        p = self.soup.new_tag("p")
        while event.name != "p":
            p.append(copy(event))
            event = event.next_sibling
        return p

    class UnreachableWikiError(Exception):
        pass

    class NoPageFound(Exception):
        pass

    class NoFirstHalfCombo(Exception):
        pass

    class NoSecondHalfCombo(Exception):
        pass

    class UncrossableSummonsException(Exception):
        pass
