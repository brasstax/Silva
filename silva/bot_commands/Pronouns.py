#!/usr/bin/env python
import logging
from discord.ext import commands
from silva.utilities import misc


class Commands(commands.Cog, name="Pronoun commands"):
    def __init__(self, bot):
        self.bot = bot
        self.db_utils = misc.Database(bot.aliases_conn)
        self.text_utils = misc.TextUtils()
        logging.info("Pronoun commands initialized.")

    @commands.command(name="pronouns", aliases=["getpronouns"])
    async def get_pronoun(self, ctx, *name: str):
        """
        Lists the pronouns for a given user.
        :param name: Either the username or the display name of a user to look up.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"get_pronoun requested by {ctx.author} in {guild}.")
        if not name:
            users = [ctx.author]
        else:
            name = " ".join(name)
            try:
                users = self.text_utils.user_searcher(self.bot, name)
            except ValueError:
                return await ctx.send(
                    "Please narrow your search (use `username#id` if needed.)"
                )
        if not users:
            await ctx.send(f'No user "{name}" found.')
        msg = ""
        for user in users:
            try:
                pronouns = await self.db_utils.get_pronouns(user.id)
                if not pronouns:
                    raise self.db_utils.MissingUserError()
                msg += f"{user.display_name} uses the following pronouns:"
                msg += f" {pronouns}"
                msg += "\n"
            except self.db_utils.MissingUserError:
                msg += f"{user.display_name} has not set their pronouns yet."
        return await ctx.send(msg)

    @commands.command(name="addpronouns", aliases=["setpronouns"])
    async def set_pronoun(self, ctx, pronouns):
        """
        Adds your pronouns.
        :param pronouns: a string of your pronouns.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"set_pronoun requested by {ctx.author} in {guild}.")
        try:
            username = f"{ctx.author.name}#{ctx.author.discriminator}"
            await self.db_utils.set_pronouns(username, ctx.author.id, pronouns)
        except ValueError:
            return await ctx.send(
                f"{ctx.author.display_name}, you have a max of 31 characters for the pronoun field."
            )
        msg = f"{ctx.author.display_name}, I have added '{pronouns}' as your pronouns."
        return await ctx.send(msg)

    @commands.command(name="delpronouns", aliases=["rmpronouns"])
    async def rm_pronoun(self, ctx):
        """
        Removes your pronouns.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"rm_pronoun requested by {ctx.author} in {guild}.")
        await self.db_utils.rm_pronouns(ctx.author.id)
        msg = f"{ctx.author.display_name}, I have removed your pronouns from the database."
        return await ctx.send(msg)
