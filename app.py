from mb import MBR
import datetime
from ext import logger
from ical_builder import IcalBuilder as ICB
from release import Release
from db.db_handler import DBHandler as DBH
from artist import Artist
import argparse

artists_path = 'parsed_artists.txt'

skip_rt = ['Compilation', 'Soundtrack', 'Spokenword', 'Interview', 'Audiobook', 'Live', 'Remix', 'DJ-mix', 'Mixtape', 'Demo', 'Bootleg', 'Other']

db = DBH('db/music.db')

argparser = argparse.ArgumentParser(description='Import artists from a file and get new releases')
argparser.add_argument('-f', '--file', help='File containing artists to import', required=False)
argparser.add_argument('-r', '--refresh', help='Refresh the releases', action='store_true')

args = argparser.parse_args()

imp = True if args.file else False

def load_artists(filepath):
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

        return Artist(fc['id'], fc['name'], dis)
    
    for a in result:
        print("No perfect match found for " + artist_name + ", choose one of the following:")
        for i, a in enumerate(result):
            print("\t" + str(i) + ": " + a['name'] + " " + a['disambiguation'])
        c = input()
        while not c.isdigit() or int(c) < 0 or int(c) >= len(result):
            c = input("Invalid choice, please enter a number between 0 and " + str(len(result) - 1) + ": ")
        a = result[int(c)]

        logger.info('Found artist: ' + a['name'])
        return Artist(a['id'], a['name'], a['disambiguation'])

"""def check_existing_artists(filepath, type='name'):
    if type == 'name':
        new_artists = load_artists(filepath)
    else:
        new_artists = [a.split(':')[1] for a in load_artists(filepath)]
    
    try:
        with open(artists_path) as file:
            ex = file.read().splitlines()
    except FileNotFoundError:
        logger.info('No existing artists found')
        return new_artists

    #split existing artists into name and id and check if the name is in the new artists
    index = 0 if type == 'name' else 1

    ex = [artist.split(':')[index].lower() for artist in ex]
    return [artist for artist in new_artists if artist.lower() not in ex]"""

def import_artists(filepath):
    new_artists = load_artists(filepath)#check_existing_artists(filepath)

    #p_file = open(artists_path).read().splitlines()

    #with open(artists_path, 'a') as file:
    for artist in new_artists:
        logger.info('Handling artist: ' + artist)
        res = handle_artist(artist)
        if res and not db.artist_id(res.mbid):
            db.add_artist(res)
            logger.info('Added artist: ' + artist)
        else:
            logger.info('Artist already in the database: ' + artist)

def get_new_releases():

    artists = db.all_artists()

    for id, mbid, name, _ in artists:
        logger.info('Getting releases for ' + name)

        offset = 0
        releases = []
        today = datetime.date.today() - datetime.timedelta(days=14)

        while True:
            rl = mb.get_release_group(mbid, 100, offset)
            releases = [r for r in rl if r['first-release-date'] >= today.isoformat()]
            if len(releases) < 100:
                break
            offset += 100

        for release in releases:
            pt = release['primary-type']
            rmbid = release['id']
            st = release.get('secondary-types', [])
            rd = release['first-release-date']
            tit = release['title']

            #if pt not in skip_rt and not any(t in skip_rt for t in st):
            tid, = db.type_id(pt)
            orid = db.release_id(rmbid)
            if not orid:
                rid = db.add_release(Release(rmbid, rd, id, tit, tid))
                logger.info('Added release: ' + tit)

            else:
                rid, = orid
                logger.info('Release already in the database: ' + tit)

            for type in st:
                stid, = db.type_id(type)
                if not db.releases_types(stid, rid):
                    db.add_type_release(stid, rid)


if __name__ == '__main__':
    mb = MBR()

    if imp:
        import_artists(args.file)

    if args.refresh:
        get_new_releases()

    builder = ICB('templates/event.ics')
    builder.build_ical(db, 'out/new_releases.ics', skip_rt)

    db.close()