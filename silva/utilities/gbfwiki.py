#!/usr/bin/env python

import requests
from bs4 import BeautifulSoup


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
        res: requests.models.Response = requests.get(self.url, params=params)
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
            event['endpoint'] = span.parent.parent.a['href']
            events.append(event)
        return events

    class UnreachableWikiError(Exception):
        pass
