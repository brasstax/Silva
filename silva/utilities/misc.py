#!/usr/bin/env python3
# misc.py
import aiosqlite
from typing import Dict


class Database():
    async def get_aliases(self, conn: str) -> Dict[str, str]:
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
