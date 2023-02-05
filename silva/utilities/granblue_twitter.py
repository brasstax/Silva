#!/usr/bin/env python
# granblue_twitter.py
# A collection of utilities to get tweet information from
# @Granblue_en.

import logging
from silva.utilities.misc import TwitterDatabase


class Twitter(object):
    def __init__(
        self,
        bot,
        discord_channel_id: int,
        twitter_database_db: str,
        twitter_database_host: str,
        twitter_database_username: str,
        twitter_database_password: str,
        twitter_usernames: str
    ):
        self.bot = bot
        self.channel_id = int(discord_channel_id)
        self.twitter_connection = f"user={twitter_database_username} password={twitter_database_password} dbname={twitter_database_db} host={twitter_database_host}"
        self.twitter_usernames = twitter_usernames
        self.client = None

    async def follow(self):
        if not self.bot.is_following:
            self.bot.is_following = True
            self.client = await TwitterDatabase.create(self.twitter_connection)
            bot = self.bot
            channel = bot.get_channel(self.channel_id)
            while True:
                for username in self.twitter_usernames:
                    tweets = await self.client.get_unread_tweets(username)
                    for tweet in tweets:
                        sid = tweet["tweet_id"]
                        logging.info(f"@{username}: {sid}")
                        url = f"https://fxtwitter.com/{username}/status/{sid}"
                        logging.info(url)
                        await channel.send(url)
                        await self.client.mark_tweet_read(username, sid)