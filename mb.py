import requests
import logging
import time

from urllib.parse import urlencode

from ext import config

logger = logging.getLogger(__name__)

class MBR:
    '''
    Class to interact with the MusicBrainz API

    Attributes:
        __last_request (int): The timestamp of the last request
        __b_url (str): The base url of the API
    '''

    def __init__(self):
        self.__last_request = 0
        self.__b_url = 'http://musicbrainz.org/ws/2/'

    def search_artist(self, artist: str, limit: int = 5) -> list:
        '''
        Searches for an artist in the MusicBrainz database
        
        Parameters:
            artist (str): The name of the artist
            limit (int): The number of results to return

        Returns:
            list: A list of found artists
        '''
        r = self.__get('artist', query=artist, limit=limit)
        if r is None:
            return []
        return r['artists']
    
    def get_release_group(self, mbid: str, limit: int, offset: int = 0) -> list:
        '''
        Gets the release groups of an artist

        Parameters:
            mbid (str): The MusicBrainz ID of the artist
            limit (int): The number of results to return
            offset (int): The offset of the results

        Returns:
            list: A list of found release groups
        '''
        r = self.__get('release-group', artist=mbid, limit=limit, offset=offset)
        if r is None:
            return []
        return r['release-groups']

    def __url_encode(self, data: dict) -> str:
        '''
        Encodes a dictionary into a url string

        Parameters:
            data (dict): The dictionary to encode

        Returns:
            str: The encoded string
        '''
        if isinstance(data, dict):
            return urlencode(data)
        
    def  __get(self, verb: str, **kw) -> dict | None:
        '''
        Sends a GET request to the MusicBrainz API

        Parameters:
            verb (str): The verb of the request
            kw (dict): The query parameters

        Returns:
            dict: The response of the request
        '''

        r_url = self.__b_url + verb + '/'

        #to respect the rate limit of 1 request per second
        if time.time() - self.__last_request < 1:
            logger.debug('sleep 1s')
            time.sleep(1)
        
        r_url += '?' + self.__url_encode(kw) + "&fmt=json"

        hdr = {'User-Agent': f"MusicBrainz Release Calendar/0.1 ({config['CREDS']['mail']})"}

        request = requests.get(r_url, headers=hdr)
        logger.debug('Requesting ' + request.url)
        self.__last_request = time.time()

        if request.status_code == 200:
            return request.json()
        return None