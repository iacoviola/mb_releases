import requests
from urllib.parse import urlencode
import time
from ext import logger, config
class MBR:

    b_url = 'http://musicbrainz.org/ws/2/' 
    
    def __init__(self) -> None:
        self.last_request = 0

    def search_artist(self, artist, limit=5):
        r = self._get('artist', query=artist, limit=limit)
        if r is None:
            return []
        return r['artists']
    
    def get_release_group(self, mbid, limit, offset=0):
        r = self._get('release-group', artist=mbid, limit=limit, offset=offset)
        if r is None:
            return []
        return r['release-groups']

    def _url_encode(self, data):
        if isinstance(data, dict):
            return urlencode(data)
        
    def  _get(self, verb, **kw):
        
        r_url = self.b_url + verb + '/'

        #to respect the rate limit of 1 request per second
        if time.time() - self.last_request < 1:
            logger.debug('sleep 1s')
            time.sleep(1)
        
        r_url += '?' + self._url_encode(kw) + "&fmt=json"

        hdr = {'User-Agent': f"MusicBrainz Release Calendar/0.1 ({config["CREDS"]["mail"]})"}

        request = requests.get(r_url, headers=hdr)
        logger.debug('Requesting ' + request.url)
        self.last_request = time.time()

        if request.status_code == 200:
            return request.json()
        return None