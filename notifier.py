from datetime import datetime as dt, timedelta as td, date as da
from time import time
from ext import logger, now
from db.db_handler import DBHandler as DBH
import requests

class Notifier:

    _md_res = ['_', '*', '[', ']', '(', ')', '~', '`', '>',
                    '#', '+', '-', '=', '|', '{', '}', '.', '!']

    _url = 'https://api.telegram.org/bot'

    _r_mb_url = 'https://musicbrainz.org/release-group/'

    _b_item_d = "*{name}* {verb} a new _{pt}{ot}_ on:\n\n*{date}*\n\n"
    _b_item_l = "Check out more at [musicbrainz\\.org]({lnk}{mbid})"
    _b_verb = ['is releasing', 'released']
    _v_selected = 0
    _db_d_f = '%Y-%m-%d'

    def __init__(self, db: DBH, tg_id, tg_token, notify_days):
        self.db = db
        self.tg_id = tg_id
        self.tg_token = tg_token
        self._url += tg_token 
        self._n_d = [int(d) for d in notify_days.split(',')]
        self._max_d = min(self._n_d)

    def _md_sanitize(self, str: str):
        for r in self._md_res:
            str = str.replace(r, '\\' + r)
        return str

    def notify(self, skip_types=[]):

        for event in self.db.get_releases(skip_types, None, None,
                                          ['last_notified'], 
                                          [{'condition': 
                                            """(last_notified IS NULL or 
                                               last_notified < date(release_date - ?))""",
                                             'params': 
                                             (self._max_d * 86400,)}], 'DESC'):
                
            logger.debug('Event: ' + str(event))

            self._v_selected = 0

            id, mbid, aid, tit, date, pt, ln = event

            ln = dt.strptime(ln , self._db_d_f).date() if ln != None else None
            date = dt.strptime(date, self._db_d_f).date()

            skip = False
            nw = da.today()

            if not ln:
                if date < nw:
                    self._v_selected = 1
            else:
                for d in self._n_d:
                    dd = date - td(days = d)
                    if nw > dd and ln <= dd:
                        skip = False
                        if d < 0:
                            self._v_selected = 1
                        break
                    else:
                        skip = True

            if not skip:
                aname, = self.db.fetchone('artists', 'name', condition=
                                        [{'condition': 'id = ?', 
                                            'params': (aid,)}])

                j = [{'table': 'types_releases', 
                    'condition': 'types.id = types_releases.type_id'}]
                w = [{'condition': 'release_id = ?', 
                    'params': (id,)}]

                ot = self.db.fetchone('types', 'name', j, w)

                if not ot:
                    rt = ""
                else:
                    rt = "(" + ", ".join(ot) + ")"

                self._send_item(id, mbid, aname, tit, date, pt, rt)


    def _send_item(self, id: str, mbid: str, aname: str, 
                 title: str, date: dt, pt: str, rt: str):
        
        d_rss = date.strftime('%A, %B %d, %Y')

        aname = self._md_sanitize(aname)
        
        msg = f"*{aname} \\- {self._md_sanitize(title)}*:\n\n"
        
        msg += self._b_item_d.format(name=self._md_sanitize(aname),
                                     verb=self._b_verb[self._v_selected],
                                     pt=self._md_sanitize(pt),
                                     ot=self._md_sanitize(rt),
                                     date=d_rss)
        
        msg += self._b_item_l.format(lnk=self._r_mb_url,
                                     mbid=self._md_sanitize(mbid))
        
        params = {'chat_id': self.tg_id,
                  'text': msg,
                  'parse_mode': 'MarkdownV2'}
        
        r = requests.post(self._url + "/sendMessage", json=params)
        
        logger.debug(r.text)
        logger.debug(msg)

        if r.status_code == 200:
            logger.info(f"Sent notification for {title} to telegram")
            self.db.update('releases', 
                            columns=('last_notified',),
                            values=(now(),), 
                            condition=[{'condition': 'id = ?', 
                                        'params': (id,)}])


