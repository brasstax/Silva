#!/usr/bin/env python

import requests
from bs4 import BeautifulSoup, element
from copy import copy
from typing import List


class wiki:
    def __init__(self, url='https://gbf.wiki'):
        self.base_url = url
        self.url = f'{self.base_url}/api.php'
        try:
            self.get_main_page()
        except Exception as e:
            raise(self.UnreachableWikiError(e))

    def get_main_page(self):
        params: dict = {
            'action': 'parse',
            'page': 'Main Page',
            'format': 'json'}
        headers: dict = {
            'User-Agent':
                'Granblue SA Silva Bot (Written by Hail Hydrate#9035)'}
        res: requests.models.Response = requests.get(
            self.url, params=params, headers=headers)
        self.soup: BeautifulSoup = BeautifulSoup(
            res.json()['parse']['text']['*'],
            features='html.parser')

    def get_current_events(self):
        '''
        Scrapes the soup for span elements containing an attribute called
        'data-text-after' with the phrase 'Event has ended', then retrieves
        the event's name, start date, end date, and wiki URL.
        return: list events
        '''
        soup = self.soup
        events: list = []
        for span in soup.find_all(
                'span', {'data-text-after': 'Event has ended.'}):
            event: dict = {}
            event['title'] = span.parent.parent.a['title']
            event_parent = span.parent.find('span', {'class': 'tooltiptext'})
            dates = event_parent.text.split('to')
            event['start'] = dates[0]
            event['finish'] = dates[1]
            event['url'] = f"{self.base_url}{span.parent.parent.a['href']}"
            events.append(event)
        return events

    def get_upcoming_events_html(self) -> List[element.Tag]:
        '''
        Scrapes the soup for a elements to identify
        the upcoming events section.
        return: list events
        '''
        soup = self.soup
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

    def get_upcoming_events(self) -> List[dict]:
        '''
        Runs get_upcoming_events_html and returns a list of dictionaries.
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
