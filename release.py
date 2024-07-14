import sqlite3
from datetime import datetime as dt

class Release:
    def __init__(self, mbid, date, artist, title, type, o_types=[]):
        self.date = dt.strptime(date, '%Y-%m-%d').date()
        self.artist = artist
        self.title = title
        self.type = type
        self.o_types = o_types
        self.mbid = mbid
        self.last_updated = dt.now().isoformat()

    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return f'{self.mbid};{self.artist};{self.title};{self.date};{self.last_updated};{self.o_types}'