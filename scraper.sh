#!/bin/bash
# scraper.sh
# Scrapes twitter using SNScrape for tweets in the environment variable
# SNSCRAPE_TWITTER_USERS (separated by commas)

which snscrape > /dev/null
[[ $? -ne 0 ]] && echo "SNScrape not installed." && exit 1;
which sqlite3 > /dev/null
[[ $? -ne 0 ]] && echo "sqlite3 not installed." && exit 1;
[[ -z ${SNSCRAPE_TWITTER_USERS} ]]  && echo "SNSCRAPE_TWITTER_USERS not set. Set SNSCRAPE_TWITTER_USERS with user handles you want to scrape, separated by comma." && exit 1;
[[ -z ${SNSCRAPE_DATABASE} ]]  && echo "SNSCRAPE_DATABASE not set. Set a path for a sqlite database that scraper.sh will use." && exit 1;
sqlite3 -batch $SNSCRAPE_DATABASE "CREATE TABLE IF NOT EXISTS tweets (username TEXT, status_id INT, date DATETIME, silva_read INT, CONSTRAINT username_status_id UNIQUE (username, status_id))"
IFS=',' read -ra USERS <<< $SNSCRAPE_TWITTER_USERS
while true; do
  for user in "${USERS[@]}"; do
    echo $user;
    IFS=' ' mapfile -t tweets < <(snscrape -n 10 --retry 3 --jsonl twitter-user $user)
    for tweet in "${tweets[@]}"; do
      username=$(echo $tweet | jq '.["user"]["username"]')
      url=$(echo $tweet | jq '.["url"]')
      IFS='/"' read -ra url_breakout <<< $url
      echo ${url_breakout[-1]}
      status_id=${url_breakout[-1]}
      date=$(echo $tweet | jq '.["date"]')
      sqlite3 -batch $SNSCRAPE_DATABASE "INSERT OR IGNORE INTO tweets(username, status_id, date, silva_read) VALUES ($username, $status_id, $date, 0)"
    done
  done
done