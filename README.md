# Silva
A Discord bot primarily used for a personal project.
Uses `py-cord` (thanks for your work on discord.py, Rapptz.)
Has various Granblue Fantasy-related commands.

# Installation
`pip install -r requirements.txt`

# Configuration
Create a `secrets` folder and the following files within it:
`discord_token.txt`
`twitter.ini`

Populate `discord_token.txt` with your Discord bot token.
Populate `twitter.ini` with the following values:
```
[default]
access_token=
access_token_secret=
api=
api_secret=
```

# Usage
`./runbot.sh config.ini`

# Logging
All command invocations log to stdout. Any tweets that come in also get logged into stdout as well.