from release import Release
from ext import logger
from datetime import datetime as dt
from db.db_handler import DBHandler as DBH

class IcalBuilder:

    prepend = 'BEGIN:VCALENDAR\nVERSION:2.0\nMETHOD:PUBLISH\nPRODID:-//hacksw/handcal//NONSGML v1.0//EN\n'
    append = 'END:VCALENDAR\n'

    def __init__(self, template_path):
        self.template = self._load_template(template_path)

    def _db_to_ical(self, date: str):
        return dt.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')
    
    def _date_to_ical(self, date: dt):
        return date.strftime('%Y%m%d')
        
    def _load_template(self, template_path):
        with open(template_path) as file:
            return file.read()
        
    def build_ical(self, db: DBH, output_path: str, skip_types=[]):
        with open(output_path, 'w') as file:
            file.write(self.prepend)

            for event in db.ical_releases(skip_types):
                
                logger.debug('Event: ' + str(event))

                id, mbid, aid, title, date, pt, = event

                aname, = db.artist_name(aid)

                other_types = [t for t, in db.release_types(id)]

                release_type = pt if not other_types else ' ('.join(other_types).join(')')

                entry = self.template.format(name=title,
                                                 artist=aname,
                                                 uid=mbid,
                                                 date=self._db_to_ical(date),
                                                 categories=pt,
                                                 type=release_type)
                logger.debug('Writing event: ' + entry)
                file.write(entry)
            file.write(self.append)
            