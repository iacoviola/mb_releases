from datetime import datetime as dt
from ext import logger, now
from db.db_handler import DBHandler as DBH
import requests

class Notifier:

    _md_res = ['_', '*', '[', ']', '(', ')', '~', '`', '>',
                    '#', '+', '-', '=', '|', '{', '}', '.', '!']

    _url = "https://api.telegram.org/bot"

    _r_mb_url = "https://musicbrainz.org/release-group/"

    _b_item_d = "*{name}* is releasing a new _{pt}{ot}_ on:\n\n*{date}*\n\n"
    _b_item_l = "Check out more at [musicbrainz\\.org]({lnk}{mbid})"

    def __init__(self, db: DBH, tg_id, tg_token):
        self.db = db
        self.tg_id = tg_id
        self.tg_token = tg_token
        self._url += tg_token 

    def _md_sanitize(self, str: str):
        for r in self._md_res:
            str = str.replace(r, '\\' + r)
        return str

    def notify(self, skip_types=[]):

        for event in self.db.get_releases(skip_types, 0, None, 
                                          [{'condition': 'notified = 0'}], 'DESC'):
                
            logger.debug('Event: ' + str(event))

            id, mbid, aid, tit, date, pt, = event
            date = dt.strptime(date, '%Y-%m-%d')

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
                rt = '(' + ', '.join(ot) + ')'

            self._send_item(id, mbid, aname, tit, date, pt, rt)


    def _send_item(self, id: str, mbid: str, aname: str, 
                 title: str, date: dt, pt: str, rt: str):
        
        d_rss = date.strftime('%A, %B %d, %Y')

        aname = self._md_sanitize(aname)
        
        msg = f'*{aname} \\- {self._md_sanitize(title)}*:\n\n'
        
        msg += self._b_item_d.format(name=self._md_sanitize(aname),
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
            logger.info(f'Sent notification for {title} to telegram')
            self.db.update('releases', 
                            columns=('notified',),
                            values=(1,), 
                            condition=[{'condition': 'id = ?', 
                                        'params': (id,)}])


