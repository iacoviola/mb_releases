from datetime import datetime as dt
from time import time
from ext import logger
import os
from db.db_handler import DBHandler as DBH

class IcalBuilder:

    _prepend = 'BEGIN:VCALENDAR\nVERSION:2.0\nMETHOD:PUBLISH\nPRODID:-//hacksw/handcal//NONSGML v1.0//EN\n'
    _append = 'END:VCALENDAR'

    def __init__(self, db: DBH, template_path):
        self.db = db
        self.template = self._load_template(template_path)
        self.ical = self._prepend

    def _db_to_ical(self, date: str):
        return dt.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')
    
    def _date_to_ical(self, date: dt):
        return date.strftime('%Y%m%d')
        
    def _load_template(self, template_path):
        with open(template_path) as file:
            return file.read()
        
    def build_ical(self, skip_types=[]):

        for event in self.db.get_releases(skip_types, None, None,
                                          ['last_updated']):
            
            logger.debug('Event: ' + str(event))

            id, mbid, aid, title, date, pt, lu = event
            date = self._db_to_ical(date)

            try:
                tstamp = dt.strptime(lu, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                tstamp = dt.strptime(lu, '%Y-%m-%dT%H:%M:%S.%f')

            tstamp = tstamp.strftime('%Y%m%dT%H%M%SZ')


            aname, = self.db.fetchone('artists', 'name', condition=
                                      [{'condition': 'id = ?', 
                                        'params': (aid,)}])

            j = [{'table': 'types_releases', 
                    'condition': 'types.id = types_releases.type_id'}]
            w = [{'condition': 'release_id = ?', 
                    'params': (id,)}]

            ot = self.db.fetchone('types', 'name', j, w)

            if not ot:
                rt = pt
            else:
                rt = '(' + ', '.join(ot) + ')'

            entry = self.template.format(name=title,
                                                artist=aname,
                                                uid=mbid,
                                                tstamp=tstamp,
                                                date=date,
                                                categories=pt,
                                                type=rt)
            logger.debug('Writing event: ' + entry)
            self.ical += entry
        self.ical += self._append
            
    def save(self, filename: str):
        with(open(filename, 'w')) as file:
            file.write(self.ical)

        os.utime(filename, (time(), time()))

        logger.info('File saved: ' + filename)