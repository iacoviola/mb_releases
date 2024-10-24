import requests
import logging

from datetime import datetime as dt, timedelta as td, date
from ext import now

from db.music_db import MusicDB as MDB

logger = logging.getLogger(__name__)

class MDSanitizer:
    __md_res = ['_', '*', '[', ']', '(', ')', '~', '`', '>',
                    '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    def sanitize(self, str: str):
        '''
        Sanitizes a string to be used in a markdown message

        Parameters:
            str (str): The string to sanitize
        Returns:
            str (str): The sanitized string
        '''
        for r in self.__md_res:
            str = str.replace(r, '\\' + r)
        return str

MDS = MDSanitizer()

class Notifier:
    '''
    Class to notify new releases to a telegram chat

    Attributes:
        __tg_url (str): The url to the telegram bot api
        __mb_url (str): The url to the musicbrainz website
        __message_h (str): The header of the message (template)
        __message_b (str): The body of the message (template)
        __message_l (str): The link of the message (template)
        __precisions (list): The precisions of the release date
        __verbs (list): The verbs of the message
        __headers (list): The headers of the message
        __db_d_f (str): The date format of the database
        __db (MDB): The database object
        __tg_id (str): The telegram chat id
        __n_d (list): The days to notify
        __min_d (int): The minimum day to notify
    '''

    def __init__(self, db: MDB, tg_id: str, tg_token: str, notify_days: str):
        self.__db = db
        self.__tg_url = 'https://api.telegram.org/bot'
        self.__mb_url = 'https://musicbrainz.org/release-group/'

        self.__message_h = "*{header}*\n\n*{a_name} \\- {r_title}*:\n\n"
        self.__message_b = "*{a_name}* {verb} a new _{pt}{ot}_ {precision}:\n\n*{r_date}*\n\n"
        self.__message_l = "Check out more at [musicbrainz\\.org]({link}{r_mbid})"

        self.__precisions = ['on', 'sometimes in']
        self.__verbs = ['is releasing', 'released']
        self.__headers = [u'\U0001F4C5' + ' Coming Soon',
                          u'\U0001F4E2' + ' Out Now' ,
                          u'\U000023F0' + ' Reminder',
                          u'\U00002728' + ' New Addition']
        self.__db_d_f = '%Y-%m-%d'

        self.__tg_id = tg_id
        self.__tg_url += tg_token 
        self.__n_d = [int(d) for d in notify_days.split(',')]
        self.__min_d = min(self.__n_d)

    def notify(self, keep_types: list = []):
        '''
        Selects and parses releases that need to be notified,
        then sends them to the telegram chat

        Parameters:
            keep_types (list): The types of releases to select
        '''
        for release in self.__db.get_releasing(keep_types, None, None,
                                          ['last_notified'], 
                                          [{'condition': 
                                            """(last_notified IS NULL or 
                                               last_notified < date(release_date, ?))""",
                                             'params': 
                                             (f'{-self.__min_d} days',)}], 
                                             'DESC'):
                
            logger.debug('Release: ' + str(release))

            s_verb = s_header = 0

            r_id, r_mbid, a_id, r_title, r_date, r_prim_type, r_lastnot = release

            if r_lastnot:
                r_lastnot = dt.strptime(r_lastnot , self.__db_d_f).date()

            is_unsure = len(r_date) <= 7
            fmt_str = self.__db_d_f[:5] if is_unsure else self.__db_d_f
            r_date = dt.strptime(r_date, fmt_str).date()

            today = date.today()

            if not is_unsure:
                if not r_lastnot:
                    s_verb = int(r_date < today)
                    s_header = 3 if r_date < today else int(r_date == today)
                else:
                    for d in self.__n_d:
                        target_day = r_date - td(days = d)
                        if today >= target_day and r_lastnot < target_day:
                            s_verb = 2 if d < 0 else int(d == 0)
                            s_header = 0 if s_verb == 0 else s_verb - 1
                            break
                    continue
            else:
                if not r_lastnot:
                    s_header = 3

            a_name = self.__db.get_artist_name(a_id)
            t_other = self.__db.get_other_types(r_id)

            data = {
                'r_id': r_id,
                'r_mbid': r_mbid,
                'a_name': a_name,
                'r_title': r_title,
                'r_date': r_date,
                'r_prim_type': r_prim_type,
                't_other': t_other
            }

            self.__send_item(data, is_unsure, s_verb, s_header)

    def __send_item(self, data: dict, is_unsure: bool,
                    s_verb: int, s_header: int):
        '''
        Shorthand method to both assemble and send a message

        Parameters:
            data (dict): Contains the release data needed to assemble the message
            is_unsure (bool): Whether the release date is uncertain
            s_verb (int): The verb to use in the message
            s_header (int): The header to use in the message
        '''

        msg = self.__assemble(data, is_unsure, s_verb, s_header)
        self.__telegram_send(msg, data['r_title'], data['r_id'])

    def __assemble(self, data: dict, is_unsure: bool,
                   s_verb: int, s_other: int):
        '''
        Assembles a message to be sent to the telegram chat
        
        Parameters:
            data (dict): Contains the release data needed to assemble the message
            is_unsure (bool): Whether the release date is uncertain
            s_verb (int): The verb to use in the message
            s_other (int): The header to use in the message
        Returns:
            str (str): The assembled message
        '''

        fmt = '%B, %Y' if is_unsure else '%A, %B %d, %Y'
        r_date = r_date.strftime(fmt)
        r_types = f"({', '.join(data['t_other'])})" if data['t_other'] else ""
        
        msg = self.__message_h.format(header=self.__headers[s_other],
                                      a_name=MDS.sanitize(data['a_name']),
                                      r_title=MDS.sanitize(data['r_title']))
        
        msg += self.__message_b.format(r_name=MDS.sanitize(data['a_name']),
                                       verb=self.__verbs[s_verb],
                                       precision=self.__precisions[int(is_unsure)],
                                       pt=MDS.sanitize(data['r_prim_type']),
                                       ot=MDS.sanitize(r_types),
                                       r_date=r_date)
        
        msg += self.__message_l.format(link=self.__mb_url,
                                       r_mbid=MDS.sanitize(data['r_mbid']))
        
        return msg        
    
    def __telegram_send(self, msg: str, r_title: str, r_id: str):
        '''  
        Sends a message to the configured telegram chat

        Parameters:
            msg (str): The message to send
            r_title (str): The title of the release
            r_id (str): The id of the release
        '''
        
        params = {'chat_id': self.__tg_id,
                  'text': msg,
                  'parse_mode': 'MarkdownV2'}
        
        result = requests.post(self.__tg_url + "/sendMessage", json=params)
        
        logger.debug("Telegram response: " + result.text)
        logger.debug("Composed message: " + msg)

        if result.status_code == 200:
            logger.info(f"Sent notification for {r_title} to telegram")
            self.__db.update(table='releases', 
                           columns=('last_notified',),
                           values=(now(),), 
                           condition=[{'condition': 'id = ?', 
                                        'params': (r_id,)}])
