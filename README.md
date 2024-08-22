# MB RELEASES

> A tool to grab release times for your favorite artists using the MusicBrainz API.

## Setup

Clone the project and create the config file:

```bash
git clone git@github.com:iacoviola/mb_releases.git
cd mb_releases
cp config.cfg.example config.cfg
```

> MusicBrainz does not require an API key, but it requires to know your email address, to contact you in case of issues or excessive use of the API. You can set the `mail` variable in the `config.cfg` file.

## Requirements

> Tested on Python 3.11 and 3.12

I strongly recommend using a virtual environment:
```bash
python3.11 -m venv ./venv

# If you use bash
source venv/bin/activate
# If you use fish
source venv/bin/activate.fish

pip install -r requirements.txt 
```

## SQLite

The program needs an **sqlite** database to store the artists and their releases, you can create it by installing the sqlite package for your system:

```bash
#Ubuntu:
sudo apt install sqlite3

#Fedora:
sudo dnf install sqlite

#Arch:
sudo pacman -S sqlite

#MacOS with Homebrew:
brew install sqlite

#Windows with Chocolatey:
choco install sqlite

#Windows with winget:
winget install sqlite.sqlite
```

Then create the database:

```bash
sqlite3 /path/to/mb_releases/db/your_db.db < /path/to/mb_releases/db/music.sql
```

> Alternatively, you can use the already esisting `music.db` empty database in the project folder.

## Usage

- Fill the `artists.txt` file with the name of the artists you want to track (**one per line**). Most of the time, the program will automatically find the correct artist, but sometimes you will need to specify the artist from the list of suggestions.

- Sometimes an artist's release type might not interest you, you can filter them out by adding the release type you **don't** want to track to the `skip_releases.txt` file (all available release types are listed in the file `available_releases.txt`). By default the program will track the following release types: `Album`, `Single`, `EP`.
- Run the program:

```bash
python app.py -f artists.txt -t rss
```

The first time you run the program, you need to specify the file you wish to import the artists from (`-f`).

The output file type (`-t`) is always required (unless `-n` is set) and can be either `ics` or `rss`.

>If you choose the rss format there are two customizations available for it in the `config.cfg` file:
>>the `d_past` option is the number of days in the past you want to see in the feed.
The `d_future` option is the number of days in the future you want to see in the feed.
If **none are set**, every release will be added to the feed.

If you want to manually refresh the releases, you can use the `-r` flag.

>Otherwise, the program will refresh the releases automatically **if** you fill the options `a_refresh` and `a_refresh_interval` in the `config.cfg` file.
>>The `a_refresh` option is either `true` or `false` and it enables the automatic refresh.
The `a_refresh_interval` is the number of days, hours and minutes between each refresh.

If you want to receive notifications on Telegram, you can use the `-n` flag.

> The program will notify you only if there are new releases, and it will not notify you if you run the program with the `-r` flag.

```bash
usage: app.py [-h] [-f FILE] [-r] [-v] -t {ics,rss}

Import artists from a file and get new releases

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  File containing artists to import
  -r, --refresh         Refresh the releases
  -v, --verbose         Verbose output
  -t {ics,rss}, --type {ics,rss}
                        Output file format
  -n, --notify          Notify new releases to telegram
```

## Telegram Bot

If you want to receive notifications on Telegram, you can do so by creating a telegram bot (use [@BotFather](https://t.me/botfather) to create one).
Copy its token and paste it in the `config.cfg` file under the `tg_token` option.

On top of this, you need to get your telegram user id, you can do so by messaging the bot [@myidbot](https://t.me/myidbot) and copying the id it gives you and pasting it in the `config.cfg` file under the `tg_id` option.

## Cron/Timer

In the future, I plan to make the program a service that runs in the background and automatically refreshes the releases at random intervals.
For the time being I don't advise running the program with a cron job, or a timer, as it would put a lot of stress on the MusicBrainz API and could get your IP banned.

Unless of course you adopt a mindful approach and only run the program once per couple of days or once a week.

```bash
# Example of a cron job that runs the program every 3 days
0 0 */3 * * /path/to/python /path/to/mb_releases/app.py -f /path/to/mb_releases/artists.txt -t rss
```

If you want to use a systemd timer, you can create a service file and a timer file and enable the timer.

```bash
# Example of a service file
# Place this file in /etc/systemd/system/mb_releases.service
[Unit]
Description=MB Releases

[Service]
Type=simple
ExecStart=/path/to/python /path/to/mb_releases/app.py -f /path/to/mb_releases/artists.txt -t rss
```

```bash
# Example of a timer that runs the program every monday at 00:00
# Place this file in /etc/systemd/system/mb_releases.timer
[Unit]
Description=MB Releases

[Timer]
OnCalendar=Mon *-*-* 00:00:00
Unit=mb_releases.service

[Install]
WantedBy=timers.target
```

Then enable the timer:

```bash
systemctl enable mb_releases.timer
systemctl start mb_releases.timer
```

**Please do not copy the examples above blindly, as they might get your IP banned from the MusicBrainz API, change the intervals to something you find reasonable.**

**But in other cases unless you know how to randomize the intervals, I advise running the program manually**
