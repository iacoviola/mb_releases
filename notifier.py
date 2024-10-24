from datetime import datetime as dt, timedelta as td, date
from ext import logger, now

from db.music_db import MusicDB as MDB

import requests
#import urllib

class Notifier:
    '''
    Class to notify new releases to a telegram chat
    '''

    _md_res = ['_', '*', '[', ']', '(', ')', '~', '`', '>',
                    '#', '+', '-', '=', '|', '{', '}', '.', '!']

    _url = 'https://api.telegram.org/bot'
    _r_mb_url = 'https://musicbrainz.org/release-group/'

    _b_item_h = "*{other}*\n\n*{aname} \\- {title}*:\n\n"
    _b_item_d = "*{name}* {verb} a new _{pt}{ot}_ {some}:\n\n*{date}*\n\n"
    _b_item_l = "Check out more at [musicbrainz\\.org]({lnk}{mbid})"
    _some = ['sometimes in', 'on']
    _b_verb = ['is releasing', 'released']
    _b_other = [u'\U0001F4C5' + ' Coming Soon',
                u'\U0001F4E2' + ' Out Now' ,
                u'\U000023F0' + ' Reminder',
                u'\U00002728' + ' New Addition']
    _s_verb = _s_other = 0
    _db_d_f = '%Y-%m-%d'

    def __init__(self, db: MDB, tg_id: str, tg_token: str, notify_days: str):
        self.db = db
        self.tg_id = tg_id
        self.tg_token = tg_token
        self._url += tg_token 
        self._n_d = [int(d) for d in notify_days.split(',')]
        self._min_d = min(self._n_d)

    def notify(self, keep_types=[]):
        '''
        Selects and parses releases that need to be notified,
        then sends them to the telegram chat

        Parameters:
            keep_types (list): The types of releases to select
        '''
        for release in self.db.get_releasing(keep_types, None, None,
                                          ['last_notified'], 
                                          [{'condition': 
                                            """(last_notified IS NULL or 
                                               last_notified < date(release_date, ?))""",
                                             'params': 
                                             (f'{-self._min_d} days',)}], 
                                             'DESC'):
                
            logger.debug('Release: ' + str(release))

            self._s_verb = 0
            self._s_other = 0

            r_id, r_mbid, a_id, r_title, r_date, r_prim_type, r_lastnot = release

            if r_lastnot:
                r_lastnot = dt.strptime(r_lastnot , self._db_d_f).date()

            is_unsure = len(r_date) <= 7
            fmt_str = self._db_d_f[:5] if is_unsure else self._db_d_f
            r_date = dt.strptime(r_date, fmt_str).date()

            today = date.today()

            if not is_unsure:
                if not r_lastnot:
                    self._s_verb = 1 if r_date < today else 0
                    self._s_other = 3
                else:
                    for d in self._n_d:
                        target_day = r_date - td(days = d)
                        if today >= target_day and r_lastnot < target_day:
                            self._s_verb = 2 if d < 0 else (1 if d == 0 else 0)
                            self._s_other = 0 if self._s_verb == 0 else self._s_verb - 1
                            break
                    continue
            else:
                if not r_lastnot:
                    self._s_other = 3

            a_name = self.db.get_artist_name(a_id)
            t_other = self.db.get_other_types(r_id)
            r_types = f"({', '.join(t_other)})" if t_other else ""

            self.__send_item(r_id, r_mbid, a_name, r_title, r_date, 
                             r_prim_type, r_types, is_unsure)

    def __send_item(self, r_id: str, r_mbid: str, a_name: str, 
                    r_title: str, r_date: dt, r_prim_type: str, 
                    r_types: str, is_unsure: bool):
        '''
        Shorthand method to both assemble and send a message

        Parameters:
            r_id (str): The id of the release
            r_mbid (str): The musicbrainz id of the release
            a_name (str): The name of the artist
            r_title (str): The title of the release
            r_date (datetime): The release date of the release
            r_prim_type (str): The primary type of the release
            r_types (str): The additional types of the release
            is_unsure (bool): Whether the release date is uncertain
        '''

        msg = self.__assemble(r_mbid, a_name, r_title, r_date, 
                              r_prim_type, r_types, is_unsure)
        self.__telegram_send(msg, r_title, r_id)

    def __assemble(self, r_mbid: str, a_name: str, 
                   r_title: str, r_date: dt, r_prim_type: str, 
                   r_types: str, is_unsure: bool):
        '''
        Assembles a message to be sent to the telegram chat
        
        Parameters:
            r_mbid (str): The musicbrainz id of the release
            a_name (str): The name of the artist
            r_title (str): The title of the release
            r_date (datetime): The release date of the release
            r_prim_type (str): The primary type of the release
            r_types (str): The additional types of the release
            is_unsure (bool): Whether the release date is uncertain
        Returns:
            str (str): The assembled message
        '''

        fmt = '%B, %Y' if is_unsure else '%A, %B %d, %Y'
        r_date = r_date.strftime(fmt)
        
        msg = self._b_item_h.format(other=self._b_other[self._s_other],
                                    aname=self.__md_sanitize(a_name),
                                    title=self.__md_sanitize(r_title))
        
        msg += self._b_item_d.format(name=self.__md_sanitize(a_name),
                                     verb=self._b_verb[self._s_verb],
                                     some=self._some[0] if is_unsure else self._some[1],
                                     pt=self.__md_sanitize(r_prim_type),
                                     ot=self.__md_sanitize(r_types),
                                     date=r_date)
        
        msg += self._b_item_l.format(lnk=self._r_mb_url,
                                     mbid=self.__md_sanitize(r_mbid))
        
        return msg        
    
    def __telegram_send(self, msg: str, r_title: str, r_id: str):
        '''  
        Sends a message to the configured telegram chat

        Parameters:
            msg (str): The message to send
            r_title (str): The title of the release
            r_id (str): The id of the release
        '''
        
        params = {'chat_id': self.tg_id,
                  'text': msg,
                  'parse_mode': 'MarkdownV2'}
        
        #TODO: replace requests with urllib
        r = requests.post(self._url + "/sendMessage", json=params)
        
        logger.debug(r.text)
        logger.debug("Composed message: " + msg)

        if r.status_code == 200:
            logger.info(f"Sent notification for {r_title} to telegram")
            self.db.update(table='releases', 
                           columns=('last_notified',),
                           values=(now(),), 
                           condition=[{'condition': 'id = ?', 
                                        'params': (r_id,)}])

    def __md_sanitize(self, str: str):
        '''
        Sanitizes a string to be used in a markdown message

        Parameters:
            str (str): The string to sanitize
        Returns:
            str (str): The sanitized string
        '''
        for r in self._md_res:
            str = str.replace(r, '\\' + r)
        return str
