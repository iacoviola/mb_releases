BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS 'artists' (
    'id' INTEGER PRIMARY KEY,
    'mbid' VARCHAR(36) NOT NULL UNIQUE,
    'name' VARCHAR(255) NOT NULL,
    'disambiguation' VARCHAR(512)
);

CREATE TABLE IF NOT EXISTS 'types' (
    'id' INTEGER PRIMARY KEY,
    'name' VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS 'releases' (
    'id' INTEGER PRIMARY KEY,
    'mbid' VARCHAR(36) NOT NULL UNIQUE,
    'artist_mbid' INTEGER NOT NULL,
    'title' VARCHAR(255) NOT NULL,
    'release_date' DATE NOT NULL,
    'last_updated' TIMESTAMP NOT NULL,
    'primary_type' INTEGER NOT NULL,
    FOREIGN KEY ('artist_mbid') REFERENCES 'artists' ('id'),
    FOREIGN KEY ('primary_type') REFERENCES 'release_types' ('id')
);

CREATE TABLE IF NOT EXISTS 'types_releases' (
    'type_id' INTEGER NOT NULL,
    'release_id' INTEGER NOT NULL,
    PRIMARY KEY ('type_id', 'release_id'),
    FOREIGN KEY ('type_id') REFERENCES 'types' ('id'),
    FOREIGN KEY ('release_id') REFERENCES 'releases' ('id')
);

INSERT INTO 'types' ('id', 'name')
VALUES
    (1, 'Album'),
    (2, 'Single'),
    (3, 'EP'),
    (4, 'Compilation'),
    (5, 'Soundtrack'),
    (6, 'Spokenword'),
    (7, 'Interview'),
    (8, 'Audiobook'),
    (9, 'Live'),
    (10, 'Remix'),
    (11, 'Mixtape'),
    (12, 'Demo'),
    (13, 'Bootleg'),
    (14, 'DJ-mix'),
    (15, 'Other');

ALTER TABLE 'artists' ADD COLUMN 'last_updated' TIMESTAMP DEFAULT NULL;

ALTER TABLE 'releases' ADD COLUMN 'notified' BOOLEAN DEFAULT FALSE;

COMMIT;