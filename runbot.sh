cd "$(dirname "$0")"
config=${1:-config.ini}
echo "using $config for config"
until /usr/bin/env python3 bot.py --config $config; do
  echo "Silva crashed with an exit code $?. Respawning..." >&2
  sleep 60
done
