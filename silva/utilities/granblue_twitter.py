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
            twitter_user_id: int):
        self.client = peony.PeonyClient(
            consumer_key=consumer,
            consumer_secret=consumer_secret,
            access_token=access,
            access_token_secret=access_secret
        )
        self.bot = bot
        self.channel_id = int(discord_channel_id)
        self.follow_id = int(twitter_user_id)

    async def follow(self):
        client = self.client
        await client.user
        bot = self.bot
        channel = bot.get_channel(self.channel_id)
        req = client.stream.statuses.filter.post(follow=self.follow_id)
        async with req as stream:
            async for tweet in stream:
                if peony.events.tweet(tweet):
                    status_id = tweet.id
                    username = tweet.user.screen_name
                    user_id = tweet.user.id
                    if user_id != self.follow_id:
                        logging.info(f'Ignoring retweet from @{username}')
                        return
                    logging.info(f"@{username}: {tweet.text}")
                    url = f"https://twitter.com/{username}/status/{status_id}"
                    logging.info(url)
                    await channel.send(url)
