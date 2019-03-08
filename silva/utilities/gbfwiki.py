#!/usr/bin/env python

import pytz
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup, element
from copy import copy
from typing import List


async def init_wiki():
    '''
    Async-creates the wiki object and sets its .soup to actual JSON.
    return: gbfwiki.wiki wiki
    '''
    wiki = Wiki()
    await wiki._init()
    return wiki


class Wiki:
    def __init__(self):
        self.base_url = 'https://gbf.wiki'
        self.url = f'{self.base_url}/api.php'

    async def _init(self):
        self.soup = await self.get_main_page()
        self.main_page_special = await self.get_main_page_special()

    async def get_main_page(self):
        params: dict = {
            'action': 'cargoquery',
            'format': 'json',
            'tables': 'event_history',
            'fields':
                'name, utc_end, utc_start, time_start, time_end, element,'
                ' wiki_page',
            'where': '(time_start >= NOW()) OR time_end >= NOW()'
            }
        headers: dict = {
            'User-Agent':
                'Granblue SA Silva Bot (Written by Hail Hydrate#9035)',
                'Accept': 'application/json'}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        self.url, params=params, headers=headers) as resp:
                    text = await resp.json()
            except Exception as e:
                raise(self.UnreachableWikiError(e))
        json_output = text['cargoquery']
        return json_output

    async def get_main_page_special(self):
        '''
        Retrieves the Special section of the main page.
        '''
        params: dict = {
            'action': 'parse',
            'format': 'json',
            'page': 'Template:MainPageSpecial',
            'prop': 'text'
        }
        headers: dict = {
            'User-Agent':
                'Granblue SA Silva Bot (Written by Hail Hydrate#9035)',
                'Accept': 'application/json'}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        self.url, params=params, headers=headers) as resp:
                    text = await resp.json()
            except Exception as e:
                raise(self.UnreachableWikiError(e))
        text_output = text['parse']['text']['*']
        html_output = BeautifulSoup(text_output, 'html.parser')
        return html_output

    def get_events(self):
        '''
        Scrapes the soup for events and sorts them into upcoming and
        current events.
        return: dict events
        '''
        soup: dict = self.soup
        events: dict = {'upcoming': [], 'current': []}
        now: datetime.datetime = datetime.now(pytz.utc)
        for span in soup:
            event: dict = {}
            event['title'] = span['title']['name']
            event['start'] = span['title']['time start']
            if span['title']['time end'] != '':
                event['finish'] = span['title']['time end']
            else:
                event['finish'] = '¯\_(ツ)_/¯'
            event['utc start'] = span['title']['utc start']
            event['utc end'] = span['title']['utc end']
            if span['title']['element'] != '':
                event['title'] += f" ({span['title']['element']})"
            if span['title']['wiki page'] != '':
                url = f"{self.base_url}/{span['title']['wiki page']}".replace(
                    ' ', '_')
                event['url'] = url
            else:
                event['url'] = 'No wiki page'
            if datetime.fromtimestamp(
                    int(span['title']['utc start'])).replace(
                        tzinfo=pytz.utc) <= now:
                events['current'].append(event)
            else:
                events['upcoming'].append(event)
        return events

    def get_special_events(self) -> List[element.Tag]:
        soup = self.main_page_special
        events: list = []
        for span in soup.find_all(
                'span', {'data-text-after': 'Event has ended.'}):
            event: dict = {}
            event['title'] = span.parent.parent.a['title']
            event_parent = span.parent.find('span', {'class': 'tooltiptext'})
            dates = event_parent.text.split('to')
            event['start'] = dates[0]
            event['finish'] = dates[1]
            event['utc start']: int = int(span['data-start'])
            event['utc end']: int = int(span['data-end'])
            event['url'] = f"{self.base_url}{span.parent.parent.a['href']}"
            events.append(event)
        return events

    def get_upcoming_events_html(self) -> List[element.Tag]:
        '''
        Scrapes the soup for a elements to identify
        the upcoming events section.
        Deprecated since we can get JSON output, but remains in case it's
        needed for a future function.
        return: list events
        '''
        soup: List(dict) = self.soup
        future_events = (
            soup.find(text='Upcoming Events')
            .parent.parent.next_sibling.next_sibling)
        events = future_events.find_all('a')
        # Check to make sure the event is properly wrapped in a <p>
        for idx, event in enumerate(events):
            if not self.is_wrapped_event(event):
                e = self.wrap_around_p(event)
                events[idx] = e
            else:
                events[idx] = event.parent
        return events

    def get_upcoming_events_by_scraping(self) -> List[dict]:
        '''
        Runs get_upcoming_events_html and returns a list of dictionaries.
        Deprecated since we can get JSON output, but remains in case it's
        needed for a future function.
        '''
        html: List[element.Tag] = self.get_upcoming_events_html()
        events: list = []
        for p in html:
            event: dict = {}
            event['title'] = p.find('a')['title']
            # Italicized special text will be added to the
            # title in parenthesis.
            if p.find('i'):
                event['title'] += f" ({p.find('i').text})"
            event['url'] = f"{self.base_url}{p.find('a')['href']}"
            # The duration is in the element after the last break.
            event['duration'] = str(p.find_all('br')[-1].next_sibling)
            # In case of duplicates, skip.
            if event not in events:
                events.append(event)
        return events

    def is_wrapped_event(self, event: element.Tag) -> bool:
        '''
        Checks to see if an upcoming event is properly wrapped in a <p>
        HTML element.
        Deprecated since we can get JSON output, but remains in case it's
        needed for a future function.
        '''
        return event.parent.name == 'p'

    def wrap_around_p(self, event: element.Tag) -> element.Tag:
        '''
        Wraps elements around a <p> tag until the function reaches the next <p>
        tag, or the end of the document.
        return clone: element.Tag
        '''
        p = self.soup.new_tag('p')
        while event.name != 'p':
            p.append(copy(event))
            event = event.next_sibling
        return p

    class UnreachableWikiError(Exception):
        pass
