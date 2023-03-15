# Silva
A Discord bot primarily used for a personal project.
Uses `discord.py`.
Has various Granblue Fantasy-related commands.

# Installation
`pip install -r requirements.txt`

# Requirements
You'll need a Postgres server set up for the twitter integration. It can just be a fresh postgres instance.
You'll also need `jq`.

# Configuration
Create a `secrets` folder and the following files within it:
`discord_token.txt`
`twitter.ini`

Populate `discord_token.txt` with your Discord bot token.

# Usage
## Twitter window
export these environment variables:

```
SNSCRAPE_TWITTER_USERS
SNSCRAPE_DATABASE_DB
SNSCRAPE_DATABASE_HOST
SNSCRAPE_DATABASE_USERNAME
SNSCRAPE_DATABASE_PASSWORD
```
Then run `scraper.sh`.

## Bot window
`./runbot.sh config.ini`

# Logging
All command invocations log to stdout. Any tweets that come in also get logged into stdout as well.