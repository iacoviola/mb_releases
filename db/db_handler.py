import sqlite3
from artist import Artist
from release import Release

class DBHandler:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def all_artists(self):
        self.cursor.execute('SELECT * FROM artists')
        return self.cursor.fetchall()

    def all_releases(self):
        self.cursor.execute('SELECT * FROM releases')
        return self.cursor.fetchall()

    def ical_releases(self, skip_types=[]):

        bq = """SELECT DISTINCT r.id, mbid, artist_mbid, title,          
                                release_date, t2.name
                    FROM releases as r
                    LEFT JOIN types_releases as tr ON r.id = tr.release_id
                    LEFT JOIN types as t ON tr.type_id = t.id
                    JOIN types as t2 ON r.primary_type = t2.id"""

        if not skip_types:
            self.cursor.execute(bq)
        else:
            placeholders = ', '.join('?' for _ in skip_types)
            self.cursor.execute(f"""{bq} 
                                WHERE t.name NOT IN ({placeholders})
                                OR t.name ISNULL""", 
                                skip_types)
        
        return self.cursor.fetchall()
    
    def artist_id(self, mbid):
        self.cursor.execute('SELECT id FROM artists WHERE mbid = ?', (mbid,))
        return self.cursor.fetchone()
    
    def release_id(self, mbid):
        self.cursor.execute('SELECT id FROM releases WHERE mbid = ?', (mbid,))
        return self.cursor.fetchone()
    
    def artist_name(self, id):
        self.cursor.execute('SELECT name FROM artists WHERE id = ?', (id,))
        return self.cursor.fetchone()
    
    def type_id(self, type):
        self.cursor.execute('SELECT id FROM types WHERE name = ?', (type,))
        return self.cursor.fetchone()
    
    def add_artist(self, artist: Artist):
        self.cursor.execute("""INSERT INTO artists(mbid, name, disambiguation)
                            VALUES (?, ?, ?)""",
                            (artist.mbid, 
                             artist.name, 
                             artist.disambiguation))
        self.conn.commit()

    def add_release(self, release: Release):
        self.cursor.execute("""INSERT INTO releases(mbid, artist_mbid, title,
                                                    release_date, last_updated,
                                                    primary_type) 
                            VALUES (?, ?, ?, ?, ?, ?)""", 
                            (release.mbid,
                             release.artist,
                             release.title,
                             release.date,
                             release.last_updated,
                             release.type))
        self.conn.commit()

        return self.cursor.lastrowid

    def add_type_release(self, type_id, release_id):
        self.cursor.execute("""INSERT INTO types_releases(type_id, release_id)
                            VALUES (?, ?)""", 
                            (type_id, 
                             release_id))
        self.conn.commit()

    def releases_types(self, type_id, release_id):
        self.cursor.execute("""SELECT name FROM types 
                                JOIN types_releases ON types.id = types_releases.type_id 
                                    WHERE type_id = ?
                                    AND release_id = ?""", 
                                (type_id, 
                                 release_id))
        return self.cursor.fetchall()
    
    def release_types(self, release_id):
        self.cursor.execute("""SELECT name FROM types 
                                JOIN types_releases ON types.id = types_releases.type_id 
                                    WHERE release_id = ?""", 
                                (release_id,))
        return self.cursor.fetchall()
    
    def type_name(self, type_id):
        self.cursor.execute('SELECT type FROM types WHERE id = ?', (type_id,))
        return self.cursor.fetchone()
    
    def close(self):
        self.conn.close()