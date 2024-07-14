import sqlite3

class Artist:
    def __init__(self, mbid, name, disambiguation):
        self.mbid = mbid
        self.name = name
        self.disambiguation = disambiguation

    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return (self.mbid, self.name, self.disambiguation)