import sqlite3
from ext import logger
from db.query_builder import QueryBuilder as QB

class DBHandler:

    _instance = None

    def __new__(cls, db_name):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DBHandler, cls).__new__(cls)
            cls.instance.conn = sqlite3.connect(db_name)
            cls.instance.cursor = cls.instance.conn.cursor()
        return cls.instance
    
    def close(self):
        self.conn.close()

    def _fetchbuild(self, table, columns='*', joins=None, wheres=None,
                    order_by=None):
        qb = QB().select(columns).table(table)
        if joins:
            for join in joins:
                qb.join(join['table'], 
                        join['condition'], 
                        join['type'] if 'type' in join else 'INNER')
        if wheres:
            for where in wheres:
                qb.where(where['condition'], where['params'])

        if order_by:
                qb.order_by(order_by['columns'],
                            order_by['direction'] 
                                if 'direction' in order_by 
                                else 'ASC')
        return qb.build_s()

    def fetchall(self, table, columns='*', joins=None, wheres=None,
                 order_by=None):
        query, params = self._fetchbuild(table, 
                                         columns, 
                                         joins, 
                                         wheres,
                                         order_by)
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    
    def fetchone(self, table, columns='*', joins=None, condition=None,
                 order_by=None):
        query, params = self._fetchbuild(table, 
                                         columns, 
                                         joins, 
                                         condition,
                                         order_by)
        self.cursor.execute(query, params)
        logger.debug(query)
        return self.cursor.fetchone()
        
    def insert(self, table, columns=(), values=()):
        lc = len(columns)
        lv = len(values)
        
        if lc == 0:
            logger.debug('No columns provided, inserting all values')
        elif lc != lv:
            raise ValueError('Columns and values must have the same length')
        
        query = f"""INSERT INTO {table} 
                    {"" if not columns else "(" + ", ".join(columns) + ")"}
                         VALUES ({", ".join(["?" for _ in values])})"""
        
        logger.debug(query)
        
        self.cursor.execute(query, values)
        self.conn.commit()

        return self.cursor.lastrowid
    
    def update(self, table, columns=(), values=(), condition=None):
        lc = len(columns)
        lv = len(values)

        if not condition:
            raise ValueError('No condition provided')

        if lc == 0:
            raise ValueError('Columns must have at least one element')
        
        if lc != lv:
            raise ValueError("Columns and values must have the same length: " + str(lc) + " != " + str(lv))
        
        q = QB().table(table).set(columns, values)
        
        for where in condition:
            q.where(where['condition'], where['params'])

        query, params = q.build_u()

        logger.debug(query)

        self.cursor.execute(query, params)
        self.conn.commit()

    def delete(self, table, condition, params=()):
        query = f"DELETE FROM {table} WHERE {condition}"
        self.cursor.execute(query, params)
        self.conn.commit()

    def get_releases(self, skip_types=[], 
                     d_past=-1, d_fut=-1,
                     add_cols=None,
                     o_condition=None, order='ASC'):

        qb = QB().select(['r.id', 'mbid', 'artist_mbid', 'title', 'release_date', 't2.name'])

        if add_cols:
            qb.select(add_cols)

        qb.table('releases AS r')
        qb.join('types_releases AS tr', 'r.id = tr.release_id', 'LEFT')
        qb.join('types AS t', 'tr.type_id = t.id', 'LEFT')
        qb.join('types AS t2', 'r.primary_type = t2.id')

        if skip_types:
            qb.where(f"""(t.name NOT IN ({", ".join(["?" for _ in skip_types])})
                        OR t.name ISNULL)""", skip_types)
        
        d_past = -1 if d_past is None else d_past
        d_fut = -1 if d_fut is None else d_fut

        if d_past >= 0:
            qb.where('r.release_date >= date("now", ?)', (f'-{d_past} days',))

        if d_fut >= 0:
            qb.where('r.release_date <= date("now", ?)', (f'+{d_fut} days',))

        if o_condition:
            for cond in o_condition:
                qb.where(cond['condition'], cond.get('params', ()))

        qb.order_by(('r.release_date', 'r.title'), order)

        query, params = qb.build_s()
        logger.debug(query)
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
        '''
        SELECT DISTINCT
            r.id,
            mbid,
            artist_mbid,
            title,
            release_date,
            t2.name,
            last_notified,
            last_updated
        FROM
            releases as r
            LEFT JOIN types_releases as tr ON r.id = tr.release_id
            LEFT JOIN types as t ON tr.type_id = t.id
            JOIN types as t2 ON r.primary_type = t2.id
        WHERE
            (
                t.name NOT IN (
                    'Album',
                    'Single',
                    'EP',
                    'Compilation',
                    'Live',
                    'Soundtrack',
                    'Remix',
                    'Bootleg',
                    'Demo',
                    'Mixtape',
                    'DJ-mix',
                    'Interview',
                    'Spokenword',
                    'Audiobook',
                    'Audio drama',
                    'Other',
                    'Unknown'
                )
                OR t.name ISNULL
            )
            AND r.release_date > date ('now', '-14 days')
            AND r.release_date <= date ('now', '+1 day')
            AND (
                last_notified IS NULL
                OR last_notified < date (release_date - ?)
            )
        ORDER BY
            r.release_date,
            r.title ASC
        '''