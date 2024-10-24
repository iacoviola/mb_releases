from datetime import date, timedelta as td

from ext import logger, args, config, now

from mb import MBR

from ical_builder import IcalBuilder as ICB
from rss_builder import RSSBuilder as RSB
from notifier import Notifier

from db.db_handler import CONFLICT as CON, STATUS as STAT
from db.music_db import MusicDB as MDB

artists_path = 'parsed_artists.txt'

is_refresh = config.getboolean('SETTINGS', 'a_refresh')
refresh_time = config.get('SETTINGS', 'a_refresh_time')

tg_id = config.get('SETTINGS', 'tg_id')
tg_token = config.get('SETTINGS', 'tg_token')

master_import_path = config.get('PATHS', 'artists')

d_past = config.getint('SETTINGS', 'd_past')
d_fut = config.getint('SETTINGS', 'd_fut')

n_days = config.get('SETTINGS', 'notify_days')

ics_path = config.get('PATHS', 'ics').split(',')
if ics_path == ['']:
    logger.warning('No path for the ics file was specified, the file will not be saved')

rss_path = config.get('PATHS', 'rss').split(',')
if rss_path == ['']:
    logger.warning('No path for the rss file was specified, the file will not be saved')

db_path = config.get('PATHS', 'db')
if not db_path:
    logger.error('No path for the database was specified')
    exit(1)

db: MDB = MDB(db_path)

chosen_artists = []
if args.pick_artists:
    chosen_artists = open(args.pick_artists).read().splitlines()

is_import = True if args.file else False

ts_fmt = '%Y-%m-%d %H:%M:%S'

def load_wanted_types(file_path: str) -> list[str]:
    '''
    Load the types of releases to notify about

    Parameters:
        file_path (str): The path to the file containing the wanted types

    Returns:
        list: The wanted types
    '''
    wanted = []
    with open(file_path) as file:
        for line in file:
            if not line.startswith(('#', '[', '\n')) and not line.isspace():
                wanted.append(line.strip())
    return wanted
    
def parse_refresh_time(conf_time: str) -> int:
    '''
    Parse the refresh time from the configuration file
    The function parses the time in the format 'XdXhXm' where X is a number

    Parameters:
        conf_time (str): The time string to parse
    
    Returns:
        int: The time in seconds
    '''
    t = {}
    tn = ''
    for c in conf_time:
        if c.isdigit():
            tn += c
        elif c in ('d', 'h', 'm'):
            t[c] = int(tn)
            tn = ''
        elif c in (' ', '\t'):
            continue
        else:
            raise ValueError("Invalid character in refresh time: '" + c + "'")
    return t.get('d', 0) * 86400 + t.get('h', 0) * 3600 + t.get('m', 0) * 60

def load_lines(file_path: str) -> tuple[list[str], int]:
    '''
    Load the lines from a file and remove empty lines and sections
    If the file contains a section [New] the function will return the index of said section

    Parameters:
        file_path (str): The path to the file to load
    
    Returns:
        tuple: The lines and the index of the new artists section
    '''
    with open(file_path) as file:
        lines = file.read().splitlines()
    
    new_artists = 0
    i = 0

    for line in lines:
        if line.startswith('\n') or line.isspace() or line.startswith('['):
            lines.pop(i)
            if line.lower().strip() == '[new]':
                new_artists = i + 1
        else:
            i += 1

    return lines, new_artists


def handle_artist(artist_name: str, auto: bool = False) -> tuple[str, str, str]:
    '''
    Search for an artist in the MusicBrainz database and return its data

    Parameters:
        artist_name (str): The name of the artist to search for
        auto (bool): Whether to automatically choose the first result or not
    
    Returns:
        tuple: The data of the artist found
    '''
    logger.info('Handling artist: ' + artist_name)
    result = mb.search_artist(artist_name)

    if not result:
        return None

    fc = result[0]

    '''
    If the first result is a perfect match and the auto flag is set, return the data
    Otherwise, ask the user to choose an artist from the list of results
    '''
    if fc['score'] in (100, 99) and auto:
        logger.info('Found artist: ' + fc['name'])

        dis = fc.get('disambiguation', None)

        return (fc['id'], fc['name'], dis)
    
    for a in result:
        if auto:
            print("No perfect match found for " + artist_name + ", choose one of the following:")
        else:
            print("Choose one of the following for " + artist_name + ":")
        for i, a in enumerate(result):
            dis = a.get('disambiguation', "")
            print("\t" + str(i) + ": " + a['name'] + f" ({dis})" if dis else "")
        c = input('number [0] -> ')
        while True:
            if c.isdigit() and int(c) >= 0 and int(c) <= len(result):
                break
            elif c == '':
                c = 0
                break
            c = input("Invalid choice, please enter a number between 0 and " + str(len(result) - 1) + ": ")
        a = result[int(c)]

        logger.info('Found artist: ' + a['name'])
        return (a['id'], a['name'], a.get('disambiguation', None))
    
def insert_artist(a_data: tuple[str, str, str]) -> str | None:
    '''
    Insert an artist into the database

    Parameters:
        a_data (tuple): The data of the artist to insert

    Returns:
        str | None: The name of the artist inserted or None if the artist was not found
    '''
    if a_data:
        artist = a_data[1]
        if db.insert_update('artists', 
                    columns=('mbid', 'name', 'disambiguation'), 
                    values=a_data,
                    conflict_columns=('mbid',))[1] == STAT.INSERT:
            logger.info('Added artist: ' + artist)
        else:
            logger.info('Artist already in the database: ' + artist)
        
        return artist
    return None

def import_artists(file_path: str, auto: bool = False):
    '''
    Import artists from a file and insert them into the database
    Adding the new artists to the master import file
    
    Parameters:
        file_path (str): The path to the file containing the artists to import
        auto (bool): Whether to automatically choose the first result or not
    '''

    all_artists, new_i = load_lines(file_path)

    if new_i == len(all_artists):
        logger.info('No new artists to import detected')
        return
    
    logger.info('Found ' + str(new_i) + ' old artists and ' + str(len(all_artists) - new_i) + ' new artists')

    old_artists = all_artists[:new_i]
    new_artists = all_artists[new_i:]

    for artist in new_artists:
        a_data = handle_artist(artist, auto)
        right_a = insert_artist(a_data)
        if not right_a:
            logger.warning('Could not find artist: ' + artist)
        else:
            old_artists.insert(0, right_a)

    with open(master_import_path, 'w') as file:
        file.write('[Added]\n')
        for line in old_artists:
            file.write(line + '\n')
        file.write('[New]\n')

def get_new_releases(force, a_ref, arts):
    '''
    Get new releases for each artist in the database

    Parameters:
        force (bool): Whether to force the refresh of all artists
        a_ref (int): The minimum time in seconds to refresh an artist
        arts (list): The list of artists to refresh
    '''

    '''
    This is the system of precedence for the parameters:
    If force is set, refresh all artists - Maximum priority
    If arts is set, refresh only the selected artists - Medium priority
    If a_ref is set, refresh only the artists that need to be refreshed - Low priority
    If none of the above are set, do not refresh any artist
    '''
    if force:
        logger.info('Forcing refresh of all artists')
        wheres = []
    elif arts:
        logger.info('Getting releases for selected artists')
        wheres = [{'condition': 'name IN (' + ', '.join(['?' for _ in arts]) + ')',
                   'params': tuple(arts)}]
    elif a_ref > 0:
        logger.info('Getting artists that need to be refreshed')
        wheres=[{'condition': """last_updated ISNULL OR 
                                 last_updated + ? < ?""",
                 'params': (a_ref, int(now('%s')))}]
    else:
        logger.info('No artists will be refreshed')
        return
    
    artists = db.fetchall('artists', ['id', 'mbid', 'name'], 
                          wheres=wheres,
                          order_by={'columns': ('last_updated',), 
                                    'order': 'DESC'})
    
    logger.info('Found ' + str(len(artists)) + ' artists to refresh')

    for id, mbid, name in artists:

        logger.info('Getting releases for ' + name)

        offset = 0
        releases = []
        today = date.today() - td(days=30)

        while True:
            LIMIT = 100
            rl = mb.get_release_group(mbid, LIMIT, offset)
            releases += [r for r in rl if r['first-release-date'] >= today.isoformat()]
            if len(rl) < LIMIT:
                break
            offset += LIMIT

        for r in releases:
            pt = r['primary-type']
            rmbid = r['id']
            st = r.get('secondary-types', [])
            rd = r['first-release-date']
            tit = r['title']
            tid = db.get_type_id(pt)

            if not tid:
                tid = db.insert('types',
                                columns=('name',),
                                values=(pt,))

            rid, stat = db.insert_update('releases',
                            columns=('mbid', 'artist_mbid', 'title',
                                     'release_date', 'last_updated',
                                     'primary_type'),
                            values=(rmbid, id, tit, rd, now(ts_fmt), tid),
                            conflict_columns=('mbid',))

            if stat == STAT.INSERT:
                logger.info('Added release: ' + tit)
            else:
                logger.info('Release already in the database: ' + tit)

            for type in st:
                stid = db.get_type_id(type)

                if stid:
                    db.insert('types_releases', values=(stid, rid),
                              conflict=CON.IGNORE)
        
        db.update('artists', 
                  columns=('last_updated',),
                  values=(now('%s'),), 
                  condition=[{'condition': 'id = ?', 
                              'params': (id,)}])

if __name__ == '__main__':
    mb = MBR()

    '''
    If the user wants to add artists from a custom file path it can do so by specifying the -i option followed by the file path
    Otherwise the master import path will be chosen
    '''
    import_path = args.file if is_import else master_import_path
    import_artists(import_path, args.auto)

    if is_refresh:
        try:
            refresh_time = parse_refresh_time(refresh_time)
            logger.debug('Refresh time: ' + str(refresh_time))
        except ValueError as e:
            logger.error(e + ', the refresh will still be performed if the -r flag was specified')
            refresh_time = -1
    else:
        refresh_time = -1

    get_new_releases(force=args.refresh, a_ref=refresh_time, arts=chosen_artists)

    keep_rt = load_wanted_types('release_types.conf')

    if args.type == 'ics' or args.type == 'all':
        builder = ICB(db, 'templates/event.ics')
        builder.build_ical(keep_rt)
        for path in ics_path:
            builder.save(path)
            
    
    if args.type == 'rss' or args.type == 'all':
        builder = RSB(db)
        builder.generate_feed(keep_rt, d_past, d_fut)
        for path in rss_path:
            builder.save(path)

    if args.notify:
        if not tg_id:
            logger.error('No Telegram ID was provided, notifications will not be sent')
        elif not tg_token:
            logger.error('No Telegram token was provided, notifications will not be sent')
        else:
            notifier = Notifier(db, tg_id, tg_token, n_days)
            notifier.notify(keep_rt)

    db.close()