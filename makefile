empty:
	rm -f db/*.db
	sqlite3 db/music.db < db/music.sql