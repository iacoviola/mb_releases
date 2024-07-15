from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime as dt
from ext import logger, now
from db.db_handler import DBHandler as DBH

class RSSBuilder:
    
    _b_item_d = "{name} is releasing a new {pt}{ot} on {date}"
    _b_item_l = "https://musicbrainz.org/release-group/{mbid}"
    _d_fmt = '%a, %d %b %Y %H:%M:%S +0000'

    def __init__(self, db: DBH):
        self.db = db
        self.title = 'MB releases feed'
        self.link = 'https://musicbrainz.org'
        self.description = 'A feed for your music releases'
        self.language = 'en-us'

    def generate_feed(self, skip_types=[]):

        self.root = Element('rss', {'version': '2.0'})
        self.channel = SubElement(self.root, 'channel')
        SubElement(self.channel, 'title').text = self.title
        SubElement(self.channel, 'link').text = self.link
        SubElement(self.channel, 'description').text = self.description
        SubElement(self.channel, 'language').text = self.language
        SubElement(self.channel, 'lastBuildDate').text = now(self._d_fmt)
        SubElement(self.channel, 'pubDate').text = ""

        for event in self.db.file_releases(skip_types, 'rss'):
                
            logger.debug('Event: ' + str(event))

            id, mbid, aid, tit, date, pt, = event
            date = dt.strptime(date, '%Y-%m-%d')

            aname, = self.db.fetchone('artists', 'name', 'mbid = ?', (aid))

            j = [{'table': 'types', 
                  'condition': 'types.id = types_releases.type_id'}]
            w = [{'condition': 'release_id = ?', 
                  'params': id}]

            ot = [t for t, in self.db.fetchone('types', 'name', j, w)]

            if not ot:
                rt = ""
            else:
                rt = '(' + ', '.join(ot) + ')'

            self.add_item(mbid, aname, tit, date, pt, rt)


    def _add_item(self, mbid: str, aname: str, 
                 title: str, date: dt, pt: str, rt: str):
        
        item = SubElement(self.channel, 'item')
        SubElement(item, 'title').text = f'{aname} - {title}'
        SubElement(item, 'link').text = self._b_item_d.format(mbid=mbid)

        SubElement(item, 'description').text = self._b_item_d.format(name=aname,
                                                                     pt=pt,
                                                                     ot=rt,
                                                                     date=date)

        date = date.strftime(self._d_fmt)

        SubElement(item, 'pubDate').text = date
        SubElement(item, 'guid').text = f'{mbid}'
        SubElement(item, 'author').text = f'{aname}'
        SubElement(item, 'category').text = f'{pt}({rt})'
         

    def save(self, filename: str):
        self.channel.find('pubDate').text = now(self._d_fmt)

        with open(filename, 'w') as file:
            file.write(tostring(self.root).decode('utf-8'))

