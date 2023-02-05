#!/bin/bash
# scraper.sh
# Scrapes twitter using SNScrape for tweets in the environment variable
# SNSCRAPE_TWITTER_USERS (separated by commas)

which snscrape > /dev/null
[[ $? -ne 0 ]] && echo "SNScrape not installed." && exit 1;
which sqlite3 > /dev/null
[[ $? -ne 0 ]] && echo "sqlite3 not installed." && exit 1;
[[ -z ${SNSCRAPE_TWITTER_USERS} ]]  && echo "SNSCRAPE_TWITTER_USERS not set. Set SNSCRAPE_TWITTER_USERS with user handles you want to scrape, separated by comma." && exit 1;
[[ -z ${SNSCRAPE_DATABASE_DB} ]]  && echo "SNSCRAPE_DATABASE_DB not set. Set the name for a postgres database that scraper.sh will use." && exit 1;
[[ -z ${SNSCRAPE_DATABASE_HOST} ]] && echo "SNSCRAPE_DATABASE_HOST not set. Set the host for a postgres host that scraper.sh will use." && exit 1;
[[ -z ${SNSCRAPE_DATABASE_USERNAME} ]] && echo "SNSCRAPE_DATABASE_USERNAME not set. Set the username for a postgres host that scraper.sh will use." && exit 1;
[[ -z ${SNSCRAPE_DATABASE_PASSWORD} ]] && echo "SNSCRAPE_DATABASE_PASSWORD not set. Set the password for a postgres host that scraper.sh will use." && exit 1;
echo "SELECT 'CREATE DATABASE ${SNSCRAPE_DATABASE_DB}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${SNSCRAPE_DATABASE_DB}')\gexec" | psql "user=$SNSCRAPE_DATABASE_USERNAME password=$SNSCRAPE_DATABASE_PASSWORD host=$SNSCRAPE_DATABASE_HOST" 
psql "user=$SNSCRAPE_DATABASE_USERNAME password=$SNSCRAPE_DATABASE_PASSWORD host=$SNSCRAPE_DATABASE_HOST dbname=$SNSCRAPE_DATABASE_DB" -c "CREATE TABLE IF NOT EXISTS tweets (username TEXT, status_id BIGINT, date TIMESTAMP WITH TIME ZONE, silva_read INT, CONSTRAINT username_status_id UNIQUE (username, status_id))"
IFS=',' read -ra USERS <<< $SNSCRAPE_TWITTER_USERS
while true; do
  for user in "${USERS[@]}"; do
    echo $user;
    IFS=' ' mapfile -t tweets < <(snscrape -n 10 --retry 3 --jsonl twitter-user $user)
    for tweet in "${tweets[@]}"; do
      username=$(echo $tweet | jq -r '.["user"]["username"]')
      url=$(echo $tweet | jq '.["url"]')
      IFS='/"' read -ra url_breakout <<< $url
      echo ${url_breakout[-1]}
      status_id=${url_breakout[-1]}
      date=$(echo $tweet | jq -r '.["date"]')
      psql "user=$SNSCRAPE_DATABASE_USERNAME password=$SNSCRAPE_DATABASE_PASSWORD host=$SNSCRAPE_DATABASE_HOST dbname=$SNSCRAPE_DATABASE_DB" -c "INSERT INTO tweets(username, status_id, date, silva_read) VALUES ('$username', $status_id, '$date', 0) ON CONFLICT (username, status_id) DO NOTHING"
    done
  done
done