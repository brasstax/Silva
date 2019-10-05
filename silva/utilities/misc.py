#!/usr/bin/env python3
# misc.py
import aiosqlite
from typing import Dict, List
import re
import random
import aiohttp
import io


class Database():
    def __init__(self, conn: str):
        self.conn = conn

    async def get_aliases(self) -> Dict[str, List[str]]:
        cmd: str = '''
        SELECT word, alias, is_proper_noun FROM aliases;
        '''
        async with aiosqlite.connect(self.conn) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(cmd) as cursor:
                aliases: dict = {}
                async for row in cursor:
                    word = row['word']
                    alias = row['alias']
                    if row['is_proper_noun']:
                        alias = alias.capitalize()
                    if word not in aliases.keys():
                        aliases[word]: list = []
                    aliases[word].append(alias)
        return aliases

    async def get_alias(self, word: str) -> List[str]:
        aliases = await self.get_aliases()
        try:
            return aliases[word]
        except KeyError:
            return None

    async def set_alias(self, word: str, alias: str, proper):
        aliases = await self.get_aliases()
        try:
            if re.search(alias, ' '.join(aliases[word]), flags=re.IGNORECASE):
                raise self.AliasExistsError
        except KeyError:
            pass
        cmd: str = '''
        INSERT INTO aliases(word, alias, is_proper_noun) VALUES
         (?, ?, ?)
        '''
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (word.lower(), alias.lower(), proper))
            await db.commit()

    async def rm_alias(self, word: str, alias: str):
        cmd: str = '''
        DELETE FROM aliases WHERE word = ? AND alias = ?;
        '''
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (word.lower(), alias.lower()))
            await db.commit()

    class AliasExistsError(Exception):
        pass


class TextUtils():
    async def regex(self, conn: str, text: str) -> str:
        '''
        Fancier matching to cover some of the issues I've found with just using
        string.replace; namely:
        * Replacing parts of non-whole words (replacing the "cat" in
        "communicate", etc)
        * Grammatical issues from the cat facts database that,
        while I could fix, I find more interesting to try and replace in-script
        (string.capitalize doesn't detect proper nouns as well as I'd like
        it to, ending a sentence without a full stop, etc.)
        :param conn (str): database connection
        :param text (str): Text to parse and make replacements
        return new_text(str)
        '''
        db = Database(conn)
        aliases = await db.get_aliases()
        for word, alias in aliases.items():
            regex = re.compile(r"\b{}s?\b".format(word), flags=re.IGNORECASE)
            choice = random.choice(alias)
            # Replace the words, but do not remove the pluralization.
            # aka "cats" should become "Songs" and not just "Song."
            if re.findall(regex, text):
                text = re.sub(
                    r"\b{}(\b)?".format(word),
                    choice,
                    text,
                    flags=re.IGNORECASE)
            # The text might be multiple sentences. We want to make sure
            # each sentence is capitalized properly.
            # Unfortunately, text.capitalize() doesn't factor in proper nouns,
            # so we split the text into multiple sentences with periods,
            # capitalize the first letter of every sentence,
            # then join them back together.
            # Splits a sentence by periods.
            sub = re.compile('\.(\s+)?')
            text_list = sub.split(text)
            new_text_list = []
            # Does a sentence start with a lowercase letter?
            lowercase = re.compile('^[a-z]')
            for x in filter(None, text_list):
                if re.match(lowercase, x):
                    letter = x[0]
                    x = letter.capitalize() + x[1:]
                new_text_list.append(x)
            # Exclude items in the text list if they have no words.
            new_text = ". ".join(
                x for x in new_text_list if re.match(r"\w+", x))
            # If there's a dangling comma from the original sentence, replace
            # it with a period.
            if new_text.endswith(','):
                new_text = new_text[:-1]
            if not new_text.endswith('.'):
                new_text += '.'
        return new_text


class EmojiUtils():
    async def get_emoji(self, cdn: str, emoji_id: str):
        '''
        Downloads the requested emoji from a given CDN.
        :param cdn (str): the CDN to use. For standard emoji, 'maxcdn'.
            For Discord's emoji, 'discord'.
        :param emoji_id (int): the ID of the emoji. For standard emoji,
            the hex value (without the leading 0x.) For Discord's custom
            emoji, the numerical ID of the emoji.
        :return tuple of io.BytesIO of the emoji picture and the image type.
        '''
        if cdn == 'maxcdn':
            emoji_url = 'https://twemoji.maxcdn.com/2/72x72/'
        if cdn == 'discord':
            emoji_url = 'https://cdn.discordapp.com/emojis/'
        try:
            async with aiohttp.ClientSession() as session:
                if cdn == 'discord':
                    resp = await session.get(
                        f'{emoji_url}/{emoji_id}.gif', timeout=10)
                    img_type = 'gif'
                    if resp.status != 200:
                        resp = await session.get(
                            f'{emoji_url}/{emoji_id}.png', timeout=10)
                        img_type = 'png'
                if cdn == 'maxcdn':
                    resp = await session.get(
                        f'{emoji_url}/{emoji_id}.png', timeout=10)
                    img_type = 'png'
                    if resp.status != 200:
                        raise self.NoEmojiFound('No emoji found.')
                return (io.BytesIO(await resp.read()), img_type)
        except self.NoEmojiFound as e:
            raise self.NoEmojiFound(e)
        except Exception as e:
            raise aiohttp.ClientResponseError(e)

    class NoEmojiFound(Exception):
        pass
