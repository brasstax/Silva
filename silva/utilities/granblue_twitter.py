#!/usr/bin/env python
# granblue_twitter.py
# A collection of utilities to get tweet information from
# @Granblue_en.

import peony
import logging


class Twitter(object):
    def __init__(
        self,
        bot,
        consumer: str,
        consumer_secret: str,
        access: str,
        access_secret: str,
        discord_channel_id: int,
        twitter_user_id,
    ):
        self.client = peony.PeonyClient(
            consumer_key=consumer,
            consumer_secret=consumer_secret,
            access_token=access,
            access_token_secret=access_secret,
        )
        self.bot = bot
        self.channel_id = int(discord_channel_id)
        self.follow_id = twitter_user_id

    async def follow(self):
        if not self.bot.is_following:
            self.bot.is_following = True
            client = self.client
            await client.user
            bot = self.bot
            channel = bot.get_channel(self.channel_id)
            req = client.stream.statuses.filter.post(follow=self.follow_id)
            async with req as stream:
                async for tweet in stream:
                    if peony.events.tweet(tweet):
                        sid = tweet.id
                        username = tweet.user.screen_name
                        user_id = tweet.user.id
                        if user_id in self.follow_id:
                            logging.info(f"@{username}: {tweet.text}")
                            url = f"https://fxtwitter.com/{username}/status/{sid}"
                            logging.info(url)
                            await channel.send(url)
