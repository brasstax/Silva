#!/usr/bin/env python3
# misc.py
import aiosqlite
from typing import Dict, List


class Database():
    async def get_aliases(self, conn: str) -> Dict[str, List[str]]:
        cmd: str = '''
        SELECT word, alias, is_proper_noun FROM aliases;
        '''
        async with aiosqlite.connect(conn) as db:
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

    async def get_alias(self, conn: str, word: str) -> List[str]:
        aliases = await self.get_aliases(conn)
        try:
            return aliases[word]
        except KeyError:
            return None
