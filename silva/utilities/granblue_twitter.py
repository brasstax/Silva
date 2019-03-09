#!/usr/bin/env python
# granblue_twitter.py
# A collection of utilities to get tweet information from
# @Granblue_en.

import tweepy
from discord.ext import commands
import logging
from tweepy import Status
import json


class TwitterAuth(object):
    def __init__(
            self,
            consumer: str,
            consumer_secret: str,
            access: str,
            access_secret: str):
        self.auth = tweepy.OAuthHandler(consumer, consumer_secret)
        self.auth.set_access_token(access, access_secret)
        self.api = tweepy.API(self.auth)


class GranblueListener(tweepy.StreamListener):
    def __init__(self, bot: commands.Bot, channel: int, user: int):
        super(GranblueListener, self).__init__()
        self.bot = bot
        self.channel_id = channel
        self.user_id = user

    async def on_data(self, raw_data):
        data = json.loads(raw_data)
        if 'in_reply_to_status_id' in data:
            status = Status.parse(self.api, data)
            if await self.on_status(status) is False:
                return False
        elif 'delete' in data:
            delete = data['delete']['status']
            if self.on_delete(delete['id'], delete['user_id']) is False:
                return False
        elif 'event' in data:
            status = Status.parse(self.api, data)
            if self.on_event(status) is False:
                return False
        elif 'direct_message' in data:
            status = Status.parse(self.api, data)
            if self.on_direct_message(status) is False:
                return False
        elif 'friends' in data:
            if self.on_friends(data['friends']) is False:
                return False
        elif 'limit' in data:
            if self.on_limit(data['limit']['track']) is False:
                return False
        elif 'disconnect' in data:
            if self.on_disconnect(data['disconnect']) is False:
                return False
        elif 'warning' in data:
            if self.on_warning(data['warning']) is False:
                return False
        else:
            logging.error("Unknown message type: " + str(raw_data))

    async def on_status(self, status):
        # Ignore retweets
        if status.user.id != self.user_id:
            return
        bot = self.bot
        channel = bot.get_channel(self.channel_id)
        screen_name = status.user.screen_name
        status = status.id
        msg = f'https://twitter.com/@{screen_name}/status/{status}'
        await channel.send(msg)

    def on_error(self, status_code):
        if status_code == 420:
            logging.warning('Twitter rate-limit in effect.')
            return True
