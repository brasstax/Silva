#!/usr/bin/env python3
# misc.py
import aiosqlite
from typing import Dict, List
import re
import random
import aiohttp
import io
import cairosvg
from datetime import datetime, date
import operator
import asyncio
import pytz
import cv2
from cv2 import dnn_superres
import numpy
from PIL import Image

# EDSR from: https://github.com/Saafke/EDSR_Tensorflow/blob/master/models/EDSR_x4.pb
MODEL = "./EDSR_x4.pb"

class Database:
    def __init__(self, conn: str):
        self.conn = conn

    async def get_aliases(self) -> Dict[str, List[str]]:
        cmd: str = """
        SELECT word, alias, is_proper_noun FROM aliases;
        """
        async with aiosqlite.connect(self.conn) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(cmd) as cursor:
                aliases: dict = {}
                async for row in cursor:
                    word = row["word"]
                    alias = row["alias"]
                    if row["is_proper_noun"]:
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
            if re.search(alias, " ".join(aliases[word]), flags=re.IGNORECASE):
                raise self.AliasExistsError
        except KeyError:
            pass
        cmd: str = """
        INSERT INTO aliases(word, alias, is_proper_noun) VALUES
         (?, ?, ?)
        """
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (word.lower(), alias.lower(), proper))
            await db.commit()

    async def rm_alias(self, word: str, alias: str):
        cmd: str = """
        DELETE FROM aliases WHERE word = ? AND alias = ?;
        """
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (word.lower(), alias.lower()))
            await db.commit()

    class AliasExistsError(Exception):
        pass

    async def get_pronouns(self, user_id: int) -> Dict[str, int]:
        cmd: str = """
        SELECT pronouns FROM pronouns
        WHERE user_id = ? LIMIT 1;
        """
        async with aiosqlite.connect(self.conn) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(cmd, (user_id,)) as cursor:
                row = await cursor.fetchone()
        if not row:
            raise self.MissingUserError("No user found.")
        pronouns = row["pronouns"]
        return pronouns

    async def set_pronouns(
        self, user: str, user_id: int, pronouns: str, max_len=31
    ) -> None:
        # Can't parameterize column names
        # (https://www.sqlite.org/cintro.html)
        # So we're doing some basic checking here
        # to make sure users aren't putting in the gettysburg address.
        if len(pronouns) >= max_len:
            raise ValueError("Pronoun too many characters.")
        try:
            await self.get_pronouns(user_id)
            cmd = """
                UPDATE pronouns
                    SET pronouns = ?, user = ?
                WHERE user_id = ?
            """
        except self.MissingUserError:
            cmd = """
                INSERT INTO pronouns(pronouns, user, user_id) VALUES (?, ?, ?)
            """
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (pronouns, user, user_id,))
            await db.commit()

    async def rm_pronouns(self, user_id: str) -> None:
        try:
            await self.get_pronouns(user_id)
            cmd = """
                UPDATE pronouns
                    SET pronouns = 0
                WHERE user_id = ?
            """
        except self.MissingUserError:
            cmd = """
                INSERT INTO pronouns(user_id, pronouns) VALUES (?, 0)
            """
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (user_id,))
            await db.commit()

    async def get_raid_roles(self) -> List[str]:
        cmd: str = """
        SELECT * from raidroles
        """
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
            cmd = """
            UPDATE raidroles
            SET role_name = ?
            WHERE role_id = ?
            """
            async with aiosqlite.connect(self.conn) as db:
                await db.execute(cmd, (role_name, role_id,))
                await db.commit()
            raise self.DuplicateRoleError(
                f'Role "{role_name}" is already in the database.'
            )
        cmd = """
            INSERT INTO raidroles(role_id, role_name) values (?, ?)
        """
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
        cmd = """
            DELETE FROM raidroles WHERE role_id = ?
        """
        async with aiosqlite.connect(self.conn) as db:
            await db.execute(cmd, (role,))
            await db.commit()

    class MissingUserError(Exception):
        pass

    class DuplicateRoleError(ValueError):
        pass

    class InvalidRoleError(ValueError):
        pass


class TextUtils:
    async def regex(self, conn: str, text: str) -> str:
        """
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
        """
        db = Database(conn)
        aliases = await db.get_aliases()
        for word, alias in aliases.items():
            regex = re.compile(r"\b{}s?\b".format(word), flags=re.IGNORECASE)
            choice = random.choice(alias)
            # Replace the words, but do not remove the pluralization.
            # aka "cats" should become "Songs" and not just "Song."
            if re.findall(regex, text):
                text = re.sub(
                    r"\b{}(\b)?".format(word), choice, text, flags=re.IGNORECASE
                )
            # The text might be multiple sentences. We want to make sure
            # each sentence is capitalized properly.
            # Unfortunately, text.capitalize() doesn't factor in proper nouns,
            # so we split the text into multiple sentences with periods,
            # capitalize the first letter of every sentence,
            # then join them back together.
            # Splits a sentence by periods.
            sub = re.compile(r"\.(\s+)?")
            text_list = sub.split(text)
            new_text_list = []
            # Does a sentence start with a lowercase letter?
            lowercase = re.compile("^[a-z]")
            for x in filter(None, text_list):
                if re.match(lowercase, x):
                    letter = x[0]
                    x = letter.capitalize() + x[1:]
                new_text_list.append(x)
            # Exclude items in the text list if they have no words.
            new_text = ". ".join(x for x in new_text_list if re.match(r"\w+", x))
            # If there's a dangling comma from the original sentence, replace
            # it with a period.
            if new_text.endswith(","):
                new_text = new_text[:-1]
            if not new_text.endswith("."):
                new_text += "."
        return new_text

    def calculate_spark(
        self, crystals: int, tens: int, singles: int
    ) -> (int, float):  # noqa
        """
        Calculates the amount of draws available and the percentage toward
        a spark draw.
        :param crystals (int): the amount of crystals a player holds.
        300 crystals for a single draw.
        :param tens (int): How many ten-draw tickets a player has.
        Worth ten draws.
        :param singles (int): How many single-draw tickets a player has.
        Worth one draw.
        Returns (total_draws: int, spark_percentage: float)
        """
        if not isinstance(crystals, int):
            raise self.InvalidDrawsError("Crystals must be a whole number")
        if not isinstance(tens, int):
            raise self.InvalidDrawsError(
                "Ten-draw tickets must be a whole number"
            )  # noqa
        if not isinstance(singles, int):
            raise self.InvalidDrawsError(
                "Single tickets must be a whole number"
            )  # noqa
        if crystals < 0:
            raise self.InvalidDrawsError("Crystals cannot be less than 0")
        if tens < 0:
            raise self.InvalidDrawsError(
                "Ten-draw tickets cannot be less than 0"
            )  # noqa
        if singles < 0:
            raise self.InvalidDrawsError("Single tickets cannot be less than 0")  # noqa
        draws = (crystals // 300) + (tens * 10) + singles
        spark_percentage = (draws / 300) * 100
        return (draws, spark_percentage)

    def calculate_skin_spark(self, crystals: int) -> (int, float):  # noqa
        """
        Calculates the amount of draws available and the percentage toward
        a skin spark draw.
        :param crystals (int): the amount of crystals a player holds.
        200 crystals for a single draw.
        Returns (total_draws: int, spark_percentage: float)
        """
        if not isinstance(crystals, int):
            raise self.InvalidDrawsError("Crystals must be a whole number")
        if crystals < 0:
            raise self.InvalidDrawsError("Crystals cannot be less than 0")
        draws = crystals // 200
        spark_percentage = (crystals / 40000) * 100
        return (draws, spark_percentage)

    def no_if_zero(self, number: int) -> str:
        """
        Returns either the string version of an integer if the integer
        isn't a zero, or the word "no" if the integer is a zero.
        """
        return str(number) if number != 0 else "no"

    def is_plural(self, number: int) -> str:
        """
        Returns either an 's' if the number provided is not equal to 1,
        or '' if the number is 1.
        Technically I could use the inflect package instead to handle cases
        where words need to end in 'es', but this is sufficient for my use
        case.
        """
        return "" if number == 1 else "s"

    def username_parser(self, username: str):
        """
        Parses a name to remove the last four discord discriminator numbers
        and strip any trailing whitespace.
        """
        match = re.search(r"#\d\d\d\d$", username)
        if match:
            discriminator = match.group()
            username = username.split(discriminator)[0]
            discriminator = discriminator[1:]
        else:
            discriminator = None
        return username.rstrip(), discriminator

    def user_searcher(self, bot, name: str, max_users=5) -> List[any]:
        """
        Searches for a username by either their username, their username
        and their numerical discriminator, or their nickname.
        """
        username, discriminator = self.username_parser(name)
        if discriminator:
            users = [
                x
                for x in bot.get_all_members()
                if x.name.lower() == username.lower()
                and x.discriminator == discriminator
            ]
        else:
            users = [
                x for x in bot.get_all_members() if x.name.lower() == username.lower()
            ]
        if not users:
            name = re.escape(name)
            users = [
                x
                for x in bot.get_all_members()
                if re.search(name.lower(), x.display_name.lower())
            ]
        if len(users) > max_users:
            raise ValueError("Too many users returned.")
        return users

    def days_since(self, date: datetime.date) -> int:
        """
        Returns the days since the given date in utc.
        """
        days = datetime.now(pytz.utc).date() - date
        return days.days

    def inflect_day(self, day: int) -> str:
        """
        https://stackoverflow.com/a/52045942
        """
        date_suffix = ["th", "st", "nd", "rd"]
        if day % 10 in [1, 2, 3] and day not in [11, 12, 13]:
            return date_suffix[day % 10]
        else:
            return date_suffix[0]

    class InvalidDrawsError(ValueError):
        pass


class EmojiUtils:
    async def get_emoji(self, cdn: str, emoji_id: str):
        """
        Downloads the requested emoji from a given CDN.
        :param cdn (str): the CDN to use. For standard emoji, 'maxcdn'.
            For Discord's emoji, 'discord'.
        :param emoji_id (int): the ID of the emoji. For standard emoji,
            the hex value (without the leading 0x.) For Discord's custom
            emoji, the numerical ID of the emoji.
        :return tuple of io.BytesIO of the emoji picture and the image type.
        """
        if cdn == "maxcdn":
            emoji_url = "https://twemoji.maxcdn.com/2/svg/"
        if cdn == "discord":
            emoji_url = "https://cdn.discordapp.com/emojis/"
        try:
            async with aiohttp.ClientSession() as session:
                if cdn == "discord":
                    resp = await session.get(f"{emoji_url}/{emoji_id}.gif", timeout=10)
                    img_type = "gif"
                    if resp.status != 200:
                        resp = await session.get(
                            f"{emoji_url}/{emoji_id}.png", timeout=10
                        )
                        img_type = "png"
                    output = io.BytesIO(await resp.read())
                    # Check the resolution of the output, and if width < 100,
                    # increase image resolution and enhance for sharpness.
                    # It won't be perfect and it won't work well for all
                    # images, but ¯\_(ツ)_/¯
                    image = Image.open(output)
                    if image.width < 100 and img_type == "png":
                        output = await self.enhance_image(output, img_type)
                    else:
                        output.seek(0)
                    return (output, img_type)
                if cdn == "maxcdn":
                    resp = await session.get(f"{emoji_url}/{emoji_id}.svg", timeout=10)
                    img_type = "png"
                    if resp.status != 200:
                        raise NoEmojiFound("No emoji found.")
                    data = await resp.read()
                    input = io.BytesIO(data)
                    output = io.BytesIO()
                    input.seek(0)
                    cairosvg.svg2png(
                        file_obj=input,
                        parent_height=128,
                        parent_width=128,
                        write_to=output,
                    )
                return (output, img_type)
        except NoEmojiFound as e:
            raise NoEmojiFound(e)
        except Exception as e:
            raise Exception(e)

    async def enhance_image(self, data: io.BytesIO, img_type: str) -> io.BytesIO:
        """
        Sharpens an incoming image. Returns an io.BytesIO representation
        of the enhanced image.
        """
        base_width = 128
        data.seek(0)
        sr = dnn_superres.DnnSuperResImpl_create()
        sr.readModel(MODEL)
        # Set desired model/scale
        sr.setModel("edsr", 4)
        # no model supports transparent pngs so far so we convert to RGB and discard alpha
        image = cv2.imdecode(numpy.frombuffer(data.read(), numpy.uint8), cv2.IMREAD_COLOR)
        data.seek(0)
        # open original image with alpha; we'll resize this image and grab just the alpha layer later
        image_with_alpha = cv2.imdecode(numpy.frombuffer(data.read(), numpy.uint8), cv2.IMREAD_UNCHANGED)
        enhanced = sr.upsample(image)
        # new resolution
        height, width, _ = enhanced.shape
        image_with_alpha = cv2.resize(image_with_alpha, (width, height), cv2.INTER_NEAREST)
        b_channel, g_channel, r_channel = cv2.split(enhanced)
        # alpha channels
        alpha_channel = cv2.split(image_with_alpha)[-1]
        # merge upsampled picture with alpha channel from resized image
        img_BGRA = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
        sharp_kernel = numpy.array([[0, -1, 0],
                                    [-1, 5,-1],
                   [                0, -1, 0]])
        wpercent = base_width / float(width)
        new_height = int(float(height) * float(wpercent))
        img_BGRA = cv2.resize(img_BGRA, (base_width, new_height), cv2.INTER_NEAREST)
        img_BGRA = cv2.filter2D(src=img_BGRA, ddepth=-1, kernel=sharp_kernel)
        _, buffer = cv2.imencode(".png", img_BGRA)
        output = io.BytesIO(buffer)
        output.seek(0)
        return output


class Dicebag:
    def __init__(self, roll: str):
        pattern = r"\d+d\d+([\+\-x\*/]\d+)?"
        roll = roll.split()
        roll = "".join(roll)
        roll = roll.strip()
        if not re.match(pattern, roll):
            raise InvalidDiceString(f"{roll} is not a valid set of dice.")
        if re.search(r"[\+\-x\*/]", roll):
            mod_pattern = r"\d+[\+\-x\*/]\d+"
            if not re.match(mod_pattern, roll.split("d")[-1]):
                raise InvalidDiceString(f"{roll} is not a valid set of dice.")
        self.roll = roll
        self.roll_dict = self.parse_dice_string(roll)
        if self.roll_dict["dice_count"] > 10000:
            raise TooManyDiceError(f"I'm not rolling more than 10,000 dice.")

    def __repr__(self):
        return f"Dicebag('{self.roll}')"

    def __str__(self):
        dice_count = self.roll_dict["dice_count"]
        dice_type = self.roll_dict["dice_type"]
        mod_type = self.roll_dict["mod_type"]
        mod_value = self.roll_dict["mod_value"]
        return f"A dicebag with {dice_count}d{dice_type} and a modifier of {mod_type}{mod_value}."

    def parse_dice_string(self, roll: str) -> Dict[str, any]:
        """
        Parses a dice roll string and returns a dict of the following:
        dice_count (int)
        dice_type (int)
        mod_value (int)
        mod_type (str)
        """
        if not re.search(r"[\+\-x\*/]", roll):
            dice_count = roll.split("d")[0]
            dice_type = roll.split("d")[-1]
            mod_value = 0
            mod_type = "+"
        else:
            dice_count = roll.split("d")[0]
            mod_type = re.search(r"[\+\-\*x/]", roll)[0]
            dice_type = roll.split("d")[-1].split(mod_type)[0]
            mod_value = roll.split("d")[-1].split(mod_type)[-1]
        try:
            int(dice_count)
            int(dice_type)
            int(mod_value)
        except ValueError:
            raise InvalidDiceString(f"{roll} is not a valid set of dice.")
        return {
            "dice_count": int(dice_count),
            "dice_type": int(dice_type),
            "mod_type": mod_type,
            "mod_value": int(mod_value)
        }

    def dice_modifier(self, mod_type: str) -> operator:
        """
        Returns an operator function based on the mod_type operator string.
        """
        operators = {
            "+": operator.add,
            "-": operator.sub,
            "x": operator.mul,
            "*": operator.mul,
            "/": operator.floordiv
        }
        return operators[mod_type]

    async def roll_dice(self) -> int:
        """
        Uses the results from parse_dice_string to roll a set of dice
        and add modifiers.
        """
        roll = self.roll_dict
        dice_total = 0
        loop = asyncio.get_event_loop()
        for i in range(roll["dice_count"]):
            dice_total += await loop.run_in_executor(None, random.randint, 1, roll["dice_type"])
        mod_operation = self.dice_modifier(roll["mod_type"])
        total = mod_operation(dice_total, roll["mod_value"])
        return total


class NoEmojiFound(Exception):
    pass


class InvalidDiceString(ValueError):
    pass


class TooManyDiceError(ValueError):
    pass
