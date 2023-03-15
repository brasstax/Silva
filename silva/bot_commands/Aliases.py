import logging
from discord.ext import commands
from silva.utilities import misc


class Commands(commands.Cog, name="Alias commands"):
    def __init__(self, bot):
        self.bot = bot
        self.db_utils = misc.Database(bot.aliases_conn)
        logging.info("Alias commands initialized.")

    @commands.command(name="alias", aliases=["aliases"])
    async def get_alias(self, ctx, word: str):
        """
        Gets the aliases for a given word.
        """
        db = self.db_utils
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"aliases requested by {ctx.author} in {guild} for {word}.")
        aliases = await db.get_alias(word)
        if not aliases:
            msg = f'No aliases found for "{word}."'
        else:
            msg = f'Aliases for "{word}": {", ".join(aliases)}'
        await ctx.send(msg)

    @commands.command(name="addalias", aliases=["setalias"], hidden=True)
    @commands.is_owner()
    async def set_alias(self, ctx, word: str, alias: str, is_proper: bool = "True"):
        """
        Adds an alias to a given word.
        :param word (str): The word to add an alias for.
        :param alias (str): The alias to add to a word.
        :param is_proper (bool): Whether the alias is a proper noun.
        """
        db = self.db_utils
        try:
            if is_proper:
                proper: int = 1
            else:
                proper: int = 0
            await db.set_alias(word, alias, proper)
            msg = f'Alias "{alias}" added for "{word}."'
            await ctx.send(msg)
        except misc.Database.AliasExistsError:
            msg = f'Alias "{alias}" already exists for "{word}."'
            await ctx.send(msg)

    @commands.command(name="rmalias", aliases=["delalias"], hidden=True)
    @commands.is_owner()
    async def rm_alias(self, ctx, word: str, alias: str):
        """
        Removes an alias from a given word.
        :param word (str): the word to remove the alias from.
        :param alias (str): the alias to remove.
        """
        db = self.db_utils
        aliases = await db.get_alias(word)
        if not aliases:
            await ctx.send(f'"{alias}" is not an alias of "{word}."')
            return
        aliases = [x.lower() for x in aliases]
        if alias not in aliases:
            await ctx.send(f'"{alias}" is not an alias of "{word}."')
        else:
            await db.rm_alias(word, alias)
            await ctx.send(f'"{alias}" removed as alias from "{word}."')
        return
