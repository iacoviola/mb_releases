import logging

from xml.etree.ElementTree import Element, SubElement, tostring

from datetime import datetime as dt

from ext import now

from db.music_db import MusicDB as MDB

logger = logging.getLogger(__name__)

class RSSBuilder:
    '''
    Class to generate an RSS feed for new releases

    Attributes:
        __db (MDB): The database object
        __f_title (str): The title of the feed
        __f_link (str): The link of the feed
        __f_desc (str): The description of the feed
        __f_lang (str): The language of the feed
        __message_b (str): The body of the message (template)
        __message_l (str): The link of the message (template)
        __db_d_f (str): The date format of the database
        __rss_link (str): The link of the rss feed
        __xml_prolog (str): The prolog of the xml
        __root (Element): The root element of the xml
        __channel (Element): The channel element of the xml
    '''

    def __init__(self, db: MDB):
        self.__db = db
        self.__f_title = 'MB releases feed'
        self.__f_link = 'https://musicbrainz.org'
        self.__f_desc = 'A feed for your music releases'
        self.__f_lang = 'en-us'

        self.__message_b = "{a_name} is releasing a new {pt}{ot} on {r_date}"
        self.__message_l = "https://musicbrainz.org/release-group/{r_mbid}"

        self.__db_d_f = '%a, %d %b %Y %H:%M:%S +0200'

        self.__rss_link = ''
        self.__xml_prolog = '<?xml version="1.0" encoding="UTF-8"?>'

        self.__root = None
        self.__channel = None

    def build_feed(self, keep_types: list = [], d_past: int = -1, d_fut: int = -1):
        '''
        Builds the feed

        Parameters:
            keep_types (list): The types of releases to select
            d_past (int): Number of days in the past to generate
            d_fut (int): Number of days in the future to generate
        '''

        self.__root = Element('rss', {'version': '2.0'})
        self.__root.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
        self.__channel = SubElement(self.__root, 'channel')
        SubElement(self.__channel, 'atom:link', 
                   {'href': self.__rss_link,
                    'rel': 'self',
                    'type': 'application/rss+xml'})
        SubElement(self.__channel, 'title').text = self.__f_title
        SubElement(self.__channel, 'link').text = self.__f_link
        SubElement(self.__channel, 'description').text = self.__f_desc
        SubElement(self.__channel, 'language').text = self.__f_lang
        SubElement(self.__channel, 'lastBuildDate').text = now(self.__db_d_f)
        SubElement(self.__channel, 'pubDate').text = ""

        for event in self.__db.get_releasing(keep_types, d_past, d_fut):
                
            logger.debug('Event: ' + str(event))

            r_id, r_mbid, a_id, r_title, r_date, r_prim_type = event
            
            try:
                r_date = dt.strptime(r_date, '%Y-%m-%d')
            except ValueError:
                logger.error('Invalid date: ' + r_date + " for release: " + r_title)
                continue

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

            self.__add_item(data)


    def __add_item(self, data: dict):
        '''
        Adds an item to the feed

        Parameters:
            data (dict): The data of the item
        '''

        r_types = f"({', '.join(data['t_other'])})" if data['t_other'] else ""
        date_p = data['r_date'].strftime('%a, %d %b')
        date_f = data['r_date'].strftime(self.__db_d_f)

        item = SubElement(self.__channel, 'item')
        SubElement(item, 'title').text = f'{data['a_name']} - {data['r_title']}'
        SubElement(item, 'link').text = self.__message_l.format(r_mbid=data['r_mbid'])
        SubElement(item, 'description').text = self.__message_b.format(a_name=data['a_name'],
                                                                       pt=data['r_prim_type'],
                                                                       ot=r_types,
                                                                       r_date=date_p)
        SubElement(item, 'pubDate').text = date_f
        SubElement(item, 'guid', {'isPermaLink': 'false'}).text = f'{data['r_id']}'
        SubElement(item, 'category').text = f'{data['r_prim_type']}{r_types}'

    def save(self, file_name: str):
        '''
        Saves the feed to a file

        Parameters:
            file_name (str): The name of the file to save the feed to
        '''
        self.__channel.find('pubDate').text = now(self.__db_d_f)

        with open(file_name, 'w') as file:
            file.write(self.__xml_prolog + tostring(self.__root).decode('utf-8'))

        logger.info('Feed saved to ' + file_name)


