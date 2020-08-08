#!/usr/bin/env python3
# misc.py
import aiosqlite
from typing import Dict, List
import re
import random
import aiohttp
import io
import cairosvg
from PIL import Image, ImageEnhance


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

    async def get_pronouns(self, user_id: int) -> Dict[str, int]:
        cmd: str = '''
        SELECT pronouns FROM pronouns
        WHERE user_id = ? LIMIT 1;
        '''
        async with aiosqlite.connect(self.conn) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(cmd, (user_id,)) as cursor:
                row = await cursor.fetchone()
        if not row:
            raise self.MissingUserError('No user found.')
        pronouns = row['pronouns']
        return pronouns

    async def set_pronouns(self, user: str, user_id: int, pronouns: str, max_len=31) -> None:
        # Can't parameterize column names
        # (https://www.sqlite.org/cintro.html)
        # So we're doing some basic checking here
        # to make sure users aren't putting in the gettysburg address.
        if len(pronouns) >= max_len:
            raise ValueError('Pronoun too many characters.')
        try:
            await self.get_pronouns(user_id)
            cmd = '''
                UPDATE pronouns
                    SET pronouns = ?, user = ?
                WHERE user_id = ?
            '''
        except self.MissingUserError:
            cmd = '''
                INSERT INTO pronouns(pronouns, user, user_id) VALUES (?, ?, ?)
            '''
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (pronouns, user, user_id,))
            await db.commit()

    async def rm_pronouns(self, user_id: str) -> None:
        try:
            await self.get_pronouns(user_id)
            cmd = '''
                UPDATE pronouns
                    SET pronouns = 0
                WHERE user_id = ?
            '''
        except self.MissingUserError:
            cmd = '''
                INSERT INTO pronouns(user_id, pronouns) VALUES (?, 0)
            '''
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (user_id,))
            await db.commit()

    async def get_raid_roles(self) -> List[str]:
        cmd: str = '''
        SELECT * from raidroles
        '''
        async with aiosqlite.connect(self.conn) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(cmd,) as cursor:
                row = await cursor.fetchall()
        return row

    async def add_raid_role(self, role_id, role_name) -> None:
        cmd = """
        SELECT * from raidroles WHERE role_id = ?
        """
        async with aiosqlite.connect(self.conn) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(cmd, (role_id,)) as cursor:
                row = await cursor.fetchone()
        if row:
            cmd = '''
            UPDATE raidroles
            SET role_name = ?
            WHERE role_id = ?
            '''
            async with aiosqlite.connect(self.conn) as db:
                await db.execute(cmd, (role_name, role_id,))
                await db.commit()
            raise self.DuplicateRoleError(f'Role "{role_name}" is already in the database.')
        cmd = '''
            INSERT INTO raidroles(role_id, role_name) values (?, ?)
        '''
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (role_id, role_name,))
            await db.commit()

    async def rm_raid_role(self, role) -> None:
        cmd = """
        SELECT * from raidroles WHERE role_id = ?
        """
        async with aiosqlite.connect(self.conn) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(cmd, (role,)) as cursor:
                row = await cursor.fetchone()
        if not row:
            raise self.InvalidRoleError(f'Role "{role}" is not in the database.')
        cmd = '''
            DELETE FROM raidroles WHERE role_id = ?
        '''
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (role,))
            await db.commit()

    class MissingUserError(Exception):
        pass

    class DuplicateRoleError(ValueError):
        pass

    class InvalidRoleError(ValueError):
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
            sub = re.compile(r'\.(\s+)?')
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

    def calculate_spark(self, crystals: int, tens: int, singles: int) -> (int, float):  # noqa
        '''
        Calculates the amount of draws available and the percentage toward
        a spark draw.
        :param crystals (int): the amount of crystals a player holds.
        300 crystals for a single draw.
        :param tens (int): How many ten-draw tickets a player has.
        Worth ten draws.
        :param singles (int): How many single-draw tickets a player has.
        Worth one draw.
        Returns (total_draws: int, spark_percentage: float)
        '''
        if not isinstance(crystals, int):
            raise self.InvalidDrawsError('Crystals must be a whole number')
        if not isinstance(tens, int):
            raise self.InvalidDrawsError('Ten-draw tickets must be a whole number')  # noqa
        if not isinstance(singles, int):
            raise self.InvalidDrawsError('Single tickets must be a whole number')  # noqa
        if crystals < 0:
            raise self.InvalidDrawsError('Crystals cannot be less than 0')
        if tens < 0:
            raise self.InvalidDrawsError('Ten-draw tickets cannot be less than 0')  # noqa
        if singles < 0:
            raise self.InvalidDrawsError('Single tickets cannot be less than 0')  # noqa
        draws = (crystals // 300) + (tens * 10) + singles
        spark_percentage = (draws / 300) * 100
        return (draws, spark_percentage)

    def calculate_skin_spark(self, crystals: int) -> (int, float):  # noqa
        '''
        Calculates the amount of draws available and the percentage toward
        a skin spark draw.
        :param crystals (int): the amount of crystals a player holds.
        200 crystals for a single draw.
        Returns (total_draws: int, spark_percentage: float)
        '''
        if not isinstance(crystals, int):
            raise self.InvalidDrawsError('Crystals must be a whole number')
        if crystals < 0:
            raise self.InvalidDrawsError('Crystals cannot be less than 0')
        draws = (crystals // 200)
        spark_percentage = (crystals / 40000) * 100
        return (draws, spark_percentage)

    def username_parser(self, username: str):
        '''
        Parses a name to remove the last four discord discriminator numbers
        and strip any trailing whitespace.
        '''
        match = re.search(r'#\d\d\d\d$', username)
        if match:
            discriminator = match.group()
            username = username.split(discriminator)[0]
            discriminator = discriminator[1:]
        else:
            discriminator = None
        return username.rstrip(), discriminator

    def user_searcher(self, bot, name: str, max_users=5) -> List[any]:
        '''
        Searches for a username by either their username, their username
        and their numerical discriminator, or their nickname.
        '''
        username, discriminator = self.username_parser(name)
        if discriminator:
            users = [x for x in bot.get_all_members() if x.name.lower() == username.lower() and x.discriminator == discriminator]
        else:
            users = [x for x in bot.get_all_members() if x.name.lower() == username.lower()]
        if not users:
            name = re.escape(name)
            users = [x for x in bot.get_all_members() if re.search(name.lower(), x.display_name.lower())]
        if len(users) > max_users:
            raise ValueError('Too many users returned.')
        return users

    class InvalidDrawsError(ValueError):
        pass


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
            emoji_url = 'https://twemoji.maxcdn.com/2/svg/'
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
                    output = io.BytesIO(await resp.read())
                    # Check the resolution of the output, and if width < 100,
                    # increase image resolution and enhance for sharpness.
                    # It won't be perfect and it won't work well for all
                    # images, but ¯\_(ツ)_/¯
                    image = Image.open(output)
                    if image.width < 100 and img_type == 'png':
                        output = await self.enhance_image(output, img_type)
                    else:
                        output.seek(0)
                    return (output, img_type)
                if cdn == 'maxcdn':
                    resp = await session.get(
                        f'{emoji_url}/{emoji_id}.svg', timeout=10)
                    img_type = 'png'
                    if resp.status != 200:
                        raise self.NoEmojiFound('No emoji found.')
                    data = await resp.read()
                    input = io.BytesIO(data)
                    output = io.BytesIO()
                    input.seek(0)
                    cairosvg.svg2png(
                        file_obj=input,
                        parent_height=128,
                        parent_width=128,
                        write_to=output
                    )
                return (output, img_type)
        except self.NoEmojiFound as e:
            raise self.NoEmojiFound(e)
        except Exception as e:
            raise Exception(e)

    async def enhance_image(
            self, data: io.BytesIO, img_type: str) -> io.BytesIO:
        '''
        Sharpens an incoming image. Returns an io.BytesIO representation
        of the enhanced image.
        '''
        data.seek(0)
        basewidth = 128
        image = Image.open(data)
        image = image.convert('RGBA')
        wpercent = basewidth / float(image.width)
        height = int(float(image.height) * float(wpercent))
        embiggened = image.resize((basewidth, height))
        enhancer = ImageEnhance.Sharpness(embiggened)
        enhanced = enhancer.enhance(2.0)
        output = io.BytesIO()
        enhanced.save(output, format=img_type)
        output.seek(0)
        return output

    class NoEmojiFound(Exception):
        pass
