from mb import MBR
import datetime as dt
from ext import logger, args, config, now
from ical_builder import IcalBuilder as ICB
from rss_builder import RSSBuilder as RSB
from db.db_handler import DBHandler as DBH

artists_path = 'parsed_artists.txt'

db = DBH('db/music.db')

imp = True if args.file else False

ts_fmt = '%Y-%m-%d %H:%M:%S'

ref = config['SETTINGS']['a_refresh']
ref_t = config['SETTINGS']['a_refresh_time']
    
def parse_refresh_time(conf_time):
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


def load_lines(filepath):
    with open(filepath) as file:
        return file.read().splitlines()

def handle_artist(artist_name):
    result = mb.search_artist(artist_name)

    if not result:
        return None

    fc = result[0]

    if fc['score'] in (100, 99):
        logger.info('Found artist: ' + fc['name'])

        dis = fc.get('disambiguation', None)

        return (fc['id'], fc['name'], dis)
    
    for a in result:
        print("No perfect match found for " + artist_name + ", choose one of the following:")
        for i, a in enumerate(result):
            print("\t" + str(i) + ": " + a['name'] + " " + a['disambiguation'])
        c = input()
        while not c.isdigit() or int(c) < 0 or int(c) >= len(result):
            c = input("Invalid choice, please enter a number between 0 and " + str(len(result) - 1) + ": ")
        a = result[int(c)]

        logger.info('Found artist: ' + a['name'])
        return (a['id'], a['name'], a['disambiguation'])

def import_artists(filepath):
    new_artists = load_lines(filepath)

    for artist in new_artists:
        logger.info('Handling artist: ' + artist)
        res = handle_artist(artist)
        if res:
            if not db.fetchone('artists', 'id', condition=
                               [{'condition': 'mbid = ?',  
                                 'params': (res[0],)}]):
                
                db.insert('artists', 
                          columns=('mbid', 'name', 'disambiguation'), 
                          values=res)
                logger.info('Added artist: ' + artist)
            else:
                logger.info('Artist already in the database: ' + artist)
        else:
            logger.warning('Could not find artist: ' + artist)

def get_new_releases(force, a_ref):

    if force:
        logger.info('Forcing refresh of all artists')
        artists = db.fetchall('artists', ['id', 'mbid', 'name'],
                              order_by={'columns': ('last_updated',), 
                                         'order': 'DESC'})
    elif a_ref > 0:
        logger.info('Getting artists that need to be refreshed')
        artists = db.fetchall('artists', 
                              ['id', 'mbid', 'name'], 
                              wheres=[{'condition': """last_updated ISNULL OR 
                                                       last_updated + ? < ?""",
                                       'params': (a_ref, int(now('%s')))}],
                              order_by={'columns': ('last_updated',), 
                                         'order': 'DESC'})
        if not artists:
            logger.info('No artists need to be refreshed')
            return
    else:
        logger.info('No artists will be refreshed')
        return

    for id, mbid, name in artists:

        logger.info('Getting releases for ' + name)

        offset = 0
        releases = []
        today = dt.date.today() - dt.timedelta(days=14)

        while True:
            LIMIT = 100
            rl = mb.get_release_group(mbid, LIMIT, offset)
            releases = [r for r in rl if r['first-release-date'] >= today.isoformat()]
            if len(releases) < LIMIT:
                break
            offset += LIMIT

        for r in releases:
            pt = r['primary-type']
            rmbid = r['id']
            st = r.get('secondary-types', [])
            rd = r['first-release-date']
            tit = r['title']

            tid, = db.fetchone('types', 'id', condition=
                               [{'condition': 'name = ?',
                                 'params': (pt,)}])
            #tid, = db.type_id(pt)
            orid = db.fetchone('releases', 'id', condition=
                               [{'condition': 'mbid = ?',
                                 'params': (rmbid,)}])
            #orid = db.release_id(rmbid)
            if not orid:
                rid = db.insert('releases',
                                columns=('mbid', 'artist_mbid', 'title',
                                         'release_date', 'last_updated',
                                         'primary_type'),
                                values=(rmbid, id, tit, rd, now(ts_fmt), tid))
                #rid = db.add_release(Release(rmbid, rd, id, tit, tid))
                logger.info('Added release: ' + tit)

            else:
                rid, = orid
                logger.info('Release already in the database: ' + tit)

            for type in st:
                stid, = db.fetchone('types', 'id', condition=
                                    [{'condition': 'name = ?',
                                      'params': (type,)}])
                #if not db.releases_types(stid, rid):

                j = [{'table': 'types_releases',
                        'condition': 'types.id = types_releases.type_id'}]
                w = [{'condition': 'type_id = ?', 'params': (stid,)},
                     {'condition': 'release_id = ?', 'params': (rid,)}]

                if not db.fetchone('types', 'id', j, w):
                    #db.add_type_release(stid, rid)
                    db.insert('types_releases', values=(stid, rid))
        
        db.update('artists', 
                  columns=('last_updated',),
                  values=(now('%s'),), 
                  condition=[{'condition': 'id = ?', 
                              'params': (id,)}])


if __name__ == '__main__':
    mb = MBR()

    if imp:
        import_artists(args.file)

    if ref in ('True', 'true', 't', 'T'):
        try:
            ts = parse_refresh_time(ref_t)
            logger.debug('Refresh time: ' + str(ts))
        except ValueError as e:
            logger.error(e + ', the refresh will still be performed if the -r flag was specified')
            ts = -1
    else:
        ts = -1

    get_new_releases(force=args.refresh, a_ref=ts)

    skip_rt = load_lines('skip_release.txt')

    if args.type == 'ics':
        builder = ICB(db, 'templates/event.ics')
        builder.build_ical(skip_rt)
        builder.save('out/new_releases.ics')
    else:
        builder = RSB(db)
        builder.generate_feed(skip_rt)
        builder.save('out/new_releases.rss')
        builder.save('/var/www/music_ical/new_releases.rss')

    db.close()