
import logging
from discord.ext import commands
from discord import Embed, Colour
import aiohttp
from silva.utilities import gbfwiki, misc
from datetime import datetime
import random
import pytz


class Commands(commands.Cog, name="GBF-related commands"):
    def __init__(self, bot):
        self.bot = bot
        self.db_utils = misc.Database(bot.conn)
        self.text_utils = misc.TextUtils()
        logging.info('Silva commands initialized.')

    @commands.command(name='sparkcalc', aliases=['spark'])
    async def calculate_spark(
            self, ctx, crystals: int = 0, singles: int = 0, tens: int = 0):
        '''
        Calculates how many draws you have and how close you are to a spark.
        :param crystals (int): the amount of crystals a player holds.
        300 crystals for a single draw. 0 by default.
        :param singles (int): How many single-draw tickets a player has.
        Worth one draw. 0 by default.
        :param tens (int): How many ten-draw tickets a player has.
        Worth ten draws. 0 by default.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'sparkcalc requested by {ctx.author} in {guild}.')
        try:
            t = self.text_utils
            draws, spark_percentage = t.calculate_spark(crystals, tens, singles)
        except misc.TextUtils.InvalidDrawsError as e:
            return await ctx.send(f'{e}, {ctx.author.display_name}')
        msg = f'{ctx.author.display_name},'
        msg += f" you have {crystals} crystal{(lambda x: 's' if x != 1 else '')(crystals)},"
        msg += f" {tens} ten-draw ticket{(lambda x: 's' if x != 1 else '')(tens)},"
        msg += f" and {singles} single-draw ticket{(lambda x: 's' if x != 1 else '')(singles)}."
        msg += f" You have **{draws} roll{(lambda x: 's' if x != 1 else '')(draws)}**."
        if spark_percentage >= 100 and spark_percentage < 200:
            msg += " You have one spark and you're"
            msg += f" {(spark_percentage % 100):.2f}%"
            msg += " closer to a spark after."
        elif spark_percentage >= 200:
            msg += f" You have {int(spark_percentage // 100)} sparks and"
            msg += f" you're {(spark_percentage % 100):.2f}% closer"
            msg += " to a spark after."
        else:
            msg += f' You are {spark_percentage:.2f}% closer'
            msg += ' to your next spark.'
        if random.randint(1, 100) <= 25 or spark_percentage >= 100:
            encouraging_msg = random.choice([
                "You've got this!",
                "Ganbaruby!",
                "<:ganbaruby:275832773464293377>",
                "<:gobu:284812336580263938>",
                "I hope you like your spark!",
                "May your spark shower you with the draws you want.",
                "Silva, with her heart of silver, believes in you!",
                "I'm excited for you and I can't wait for your spark."
            ])
            msg += f" {encouraging_msg}"
        if crystals == 0 and singles == 0 and tens == 0:
            msg += (
                "\n If you're not sure how this command works, check the"
                ' help on "sparkcalc".')
        return await ctx.send(msg)

    @commands.command(name='skinsparkcalc', aliases=['skincalc'])
    async def calculate_spark(
            self, ctx, crystals: int = 0):
        '''
        Calculates how many draws you have and how close you are to a spark
        the new skin gacha. Presumably, this only takes crystals.
        :param crystals (int): the amount of crystals a player holds.
        200 crystals for a single draw. 0 by default.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'skinsparkcalc requested by {ctx.author} in {guild}.')
        try:
            t = self.text_utils
            draws, spark_percentage = t.calculate_skin_spark(crystals)
        except misc.TextUtils.InvalidDrawsError as e:
            return await ctx.send(f'{e}, {ctx.author.display_name}')
        msg = f'{ctx.author.display_name},'
        msg += f" you have {crystals} crystal{(lambda x: 's' if x != 1 else '')(crystals)}."
        msg += f" You have **{draws} roll{(lambda x: 's' if x != 1 else '')(draws)}**."
        if spark_percentage >= 100 and spark_percentage < 200:
            msg += " You have one spark and you're"
            msg += f" {(spark_percentage % 100):.2f}%"
            msg += " closer to a spark after."
        elif spark_percentage >= 200:
            msg += f" You have {int(spark_percentage // 100)} sparks and"
            msg += f" you're {(spark_percentage % 100):.2f}% closer"
            msg += " to a spark after."
        else:
            msg += f' You are {spark_percentage:.2f}% closer'
            msg += ' to your next spark.'
        if random.randint(1, 100) <= 25 or spark_percentage >= 100:
            encouraging_msg = random.choice([
                "You've got this!",
                "Ganbaruby!",
                "<:ganbaruby:275832773464293377>",
                "<:gobu:284812336580263938>",
                "I hope you like your spark!",
                "May your spark shower you with the draws you want.",
                "Silva, with her heart of silver, believes in you!",
                "I'm excited for you and I can't wait for your spark."
            ])
            msg += f" {encouraging_msg}"
        if crystals == 0:
            msg += (
                "\n If you're not sure how this command works, check the"
                ' help on "sparkcalc".')
        return await ctx.send(msg)

    @commands.command(name='song', aliases=['tweyen'])
    async def song(self, ctx):
        '''
        Gets a fact about Song. Or Tweyen. Depends on Silva's mood.
        '''
        bot = self.bot
        text_utils = self.text_utils
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://www.pycatfacts.com/catfacts.txt?sfw=true',
                        timeout=10) as fact:
                    status = fact.status
                    text = await fact.text()
            if status >= 400:
                new_text = random.choice(
                    [
                        'Hic... _hic..._ Soooooooong...where are youuuuu....',
                        'Heyyyyyy. Another beer! I ran out!',
                        'I love beer. More beeeeeeeeeeer!',
                        'Zzzzzz...',
                        'Beer! Beer! Beer! Beer! Beer!'
                    ]
                )
                new_text += " (Silva has had a bit too much to drink."
                app_info = await self.bot.application_info()
                owner = app_info.owner
                new_text += (
                    f" {owner.mention},"
                    " please check why Silva isn't working right.)")
                logging.info(f'Status from server: {status} {text}')
            else:
                new_text = await text_utils.regex(bot.conn, text)
            await ctx.send(new_text)
            guild = ctx.guild if ctx.guild else 'a direct message'
            logging.info(f'song requested by {ctx.author} in {guild}.')
        except Exception as e:
            logging.warning(f'Could not get cat fact: {e}')
            await ctx.send("I couldn't get a fact at this time, sorry!")

    @commands.command()
    async def events(self, ctx):
        '''
        Gets information from gbf.wiki on current and future events.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'events requested by {ctx.author} in {guild}.')
        thinking_msg = 'One sec, grabbing the current and upcoming events.'
        msg = await ctx.send(thinking_msg)
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        try:
            wiki = await gbfwiki.init_wiki()
            events = wiki.get_events()
            msg_current = Embed(
                title='Granblue Fantasy Current Events',
                url='https://gbf.wiki',
                color=Colour.teal(),
                timestamp=now)
            for event in events['current']:
                msg_current.add_field(
                    name=f"[{event['title']}]({event['url']})",
                    value=f"Ends on {event['finish']}",
                    inline=False
                )
            msg_upcoming = Embed(
                title='Granblue Fantasy Upcoming Events',
                url='https://gbf.wiki',
                color=Colour.dark_purple(),
                timestamp=now)
            for event in events['upcoming']:
                msg_upcoming.add_field(
                    name=f"[{event['title']}]({event['url']})",
                    value=f"{event['start']} to {event['finish']}",
                    inline=False
                )
            # send to a dedicated event channel if the message is not a DM
            if ctx.guild:
                events_channel = self.bot.get_channel(self.bot.events_channel)
            else:
                events_channel = ctx
            # If the event channel exists, search to see if the bot has posted
            # existing events before. If so, edit those instead of sending
            # a new embed. Best used for an events channel that is locked to
            # posting only by the bot.
            if ctx.guild:
                existing_messages = []
                async for message in events_channel.history(limit=200):
                    # Assume the first message to edit is the current events,
                    # and the second message is the upcoming events.
                    if message.author == self.bot.user and message.pinned:
                        existing_messages.append(message)
                    if len(existing_messages) >= 2:
                        break
                if not existing_messages:
                    await events_channel.send(embed=msg_current)
                    await events_channel.send(embed=msg_upcoming)
                else:
                    await existing_messages[0].edit(embed=msg_current)
                    await existing_messages[1].edit(embed=msg_upcoming)
            else:
                await events_channel.send(embed=msg_current)
                await events_channel.send(embed=msg_upcoming)
            if ctx.guild:
                mention_msg = (
                    f'Hi {ctx.author.mention}! I posted the current and'
                    f' upcoming events in {events_channel.mention}.')
            else:
                mention_msg = 'Here you go!'
            await msg.edit(content=mention_msg)
        except Exception as e:
            logging.warning(f'Could not retrieve events: {e}')
            await msg.edit(
                content="I couldn't retrieve the events at this time.")

    @commands.command(name="add-my-role", aliases=['addmyrole'])
    async def add_raid_role(self, ctx, *, role_name: str):
        '''
        Adds a role to yourself. The role must exist in the #how_to_raid channel.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'add-my-role requested by {ctx.author} in {guild} to add role "{role_name}" to themselves.')
        roles = await self.db_utils.get_raid_roles()
        message = ctx.message
        role_names = [role['role_name'].lower() for role in roles]
        if role_name.lower() not in role_names:
            logging.warning(f"{ctx.author} tried to add {role_name} but that's not in the role database.")
            return await message.add_reaction("❌")
        role_id = [role['role_id'] for role in roles if role['role_name'].lower() == role_name.lower()][0]
        role = message.guild.get_role(role_id)
        await ctx.author.add_roles(role)
        return await message.add_reaction("🆗")

    @commands.command(name="del-my-role", aliases=['rmmyrole', 'delmyrole'])
    async def rm_raid_role(self, ctx, *, role_name: str):
        '''
        Removes a raid role from yourself.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'del-my-raid-role requested by {ctx.author} in {guild} to remove role "{role_name}" from themselves.')
        roles = await self.db_utils.get_raid_roles()
        message = ctx.message
        role_names = [role['role_name'].lower() for role in roles]
        if role_name.lower() not in role_names:
            logging.warning(f"{ctx.author} tried to remove {role_name} from themselves, but that's not in the role database.")
            return await message.add_reaction("❌")
        role_id = [role['role_id'] for role in roles if role['role_name'].lower() == role_name.lower()][0]
        role = message.guild.get_role(role_id)
        await ctx.author.remove_roles(role)
        return await message.add_reaction("🆗")

    @commands.command(name='list-db-roles', aliases=['lsdbroles'])
    @commands.has_any_role("admin", "admin 2.0", "officer")
    async def list_db_raid_roles(self, ctx):
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'list-db-raid-roles requested by {ctx.author} in {guild}.')
        message = ctx.message
        roles = await self.db_utils.get_raid_roles()
        msg = "The following raid roles exist: "
        for role in roles:
            msg += f"**{role['role_name']}**{'.' if roles[-1]['role_name'] == role['role_name'] else ', '}"
        await ctx.send(msg)
        return await message.add_reaction("🆗")

    @commands.command(name="add-db-role", aliases=["adddbrole"])
    @commands.has_any_role("admin", "admin 2.0")
    async def new_raid_role_db(self, ctx, *, role_name: str):
        '''
        Adds a new raid role to the database.
        The raid role still has to actually exist in Discord for user-facing
        add/remove raid role commands to work.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'add-db-raid-role requested by {ctx.author} in {guild}.')
        message = ctx.message
        role = [role for role in message.guild.roles if role.name.lower() == role_name.lower()]
        if len(role) < 1:
            await ctx.send(f"Role '{role_name}' does not exist on this server.")
            raise ValueError(f"Role '{role_name}' does not exist on this server.")
        role = role[0]
        try:
            await self.db_utils.add_raid_role(role.id, role.name)
            logging.info(f'{ctx.author} added role "{role_name}" to role database.')
            return await message.add_reaction("🆗")
        except misc.Database.DuplicateRoleError as e:
            logging.warning(e)
            return await ctx.send(e)
        except Exception as e:
            logging.warning(e)
            return await message.add_reaction("❌")

    @commands.command(name="rm-db-role", aliases=["deldbrole", "rmdbrole"])
    @commands.has_any_role("admin", "admin 2.0")
    async def rm_raid_role_db(self, ctx, *, role_name: str):
        '''
        Removes a raid role from the database.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'rm-db-raid-role requested by {ctx.author} in {guild}.')
        message = ctx.message
        role = [role for role in message.guild.roles if role.name.lower() == role_name.lower()]
        if len(role) < 1:
            await ctx.send(f"Role '{role_name}' does not exist on this server.")
            raise ValueError(f"Role '{role_name}' does not exist on this server.")
        role = role[0]
        try:
            await self.db_utils.rm_raid_role(role.id)
            return await message.add_reaction("🆗")
        except misc.Database.InvalidRoleError as e:
            logging.warning(e)
            return await ctx.send(f"Role '{role_name}' is not in the database.")
        except Exception as e:
            logging.warning(e)
            return await message.add_reaction("❌")
