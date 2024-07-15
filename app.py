from mb import MBR
import datetime as dt
from ext import logger, args
from ical_builder import IcalBuilder as ICB
from rss_builder import RSSBuilder as RSB
from db.db_handler import DBHandler as DBH

artists_path = 'parsed_artists.txt'

db = DBH('db/music.db')

imp = True if args.file else False

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
        if res and not db.fetchone('artists', 'id', 'mbid = ?', (res.mbid)):
            db.insert('artists', values=res)
            logger.info('Added artist: ' + artist)
        else:
            logger.info('Artist already in the database: ' + artist)

def get_new_releases():

    artists = db.fetchall('artists', ['id', 'mbid', 'name'])

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

            tid, = db.fetchone('types', 'id', 'name = ?', (pt))
            #tid, = db.type_id(pt)
            orid = db.fetchone('releases', 'id', 'mbid = ?', (rmbid))
            #orid = db.release_id(rmbid)
            if not orid:
                rid = db.insert('releases', values=(rmbid, rd, id, tit, tid))
                #rid = db.add_release(Release(rmbid, rd, id, tit, tid))
                logger.info('Added release: ' + tit)

            else:
                rid, = orid
                logger.info('Release already in the database: ' + tit)

            for type in st:
                stid, = db.fetchone('types', 'id', 'name = ?', (type))
                #if not db.releases_types(stid, rid):

                j = [{'table': 'types_releases',
                        'condition': 'types.id = types_releases.type_id'}]
                w = [{'condition': 'type_id = ?', 'params': stid},
                     {'condition': 'release_id = ?', 'params': rid}]

                if not db.fetchone('types', 'id', j, w):
                    #db.add_type_release(stid, rid)
                    db.insert('types_releases', values=(stid, rid))


if __name__ == '__main__':
    mb = MBR()

    if imp:
        import_artists(args.file)

    if args.refresh:
        get_new_releases()

    skip_rt = load_lines('skip_release.txt')

    if args.type == 'ics':
        builder = ICB(db, 'templates/event.ics')
        builder.build_ical(skip_rt)
        builder.save('out/new_releases.ics')
    else:
        builder = RSB()
        builder.generate_feed(db, skip_rt)
        #builder.save('out/new_releases.rss')
        builder.save('/var/www/music_ical/new_releases.rss')

    db.close()