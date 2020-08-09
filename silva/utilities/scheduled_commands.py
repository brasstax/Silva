#!/usr/bin/env python
# scheduled_commands.py

from silva.utilities import gbfwiki
from discord import Embed, Colour
from datetime import datetime
import asyncio
import pytz
import logging


class ScheduledEvents:
    def __init__(self, bot):
        self.bot = bot

    async def update_events(self, interval: int = 1):
        """
        Updates the events channel.
        :interval (int): The interval in hours to update.
        """
        bot = self.bot
        await bot.wait_until_ready()
        channel = bot.get_channel(bot.events_channel)
        logging.info(f"update_events being ran on {channel}.")
        while bot.is_ready():
            logging.info("sending an event update.")
            seconds = interval * 3600
            now = datetime.utcnow().replace(tzinfo=pytz.utc)
            wiki = await gbfwiki.init_wiki()
            events = wiki.get_events()
            msg_current = Embed(
                title="Granblue Fantasy Current Events",
                url="https://gbf.wiki",
                color=Colour.teal(),
                timestamp=now,
            )
            for event in events["current"]:
                msg_current.add_field(
                    name=f"[{event['title']}]({event['url']})",
                    value=f"Ends on {event['finish']}",
                    inline=False,
                )
            msg_upcoming = Embed(
                title="Granblue Fantasy Upcoming Events",
                url="https://gbf.wiki",
                color=Colour.dark_purple(),
                timestamp=now,
            )
            for event in events["upcoming"]:
                msg_upcoming.add_field(
                    name=f"[{event['title']}]({event['url']})",
                    value=f"{event['start']} to {event['finish']}",
                    inline=False,
                )
            existing_messages = []
            async for message in channel.history(limit=200):
                # Assume the first message to edit is the current events,
                # and the second message is the upcoming events.
                if message.author == bot.user and message.pinned:
                    existing_messages.append(message)
                if len(existing_messages) >= 2:
                    break
            await existing_messages[0].edit(embed=msg_current)
            await existing_messages[1].edit(embed=msg_upcoming)
            await asyncio.sleep(seconds)
