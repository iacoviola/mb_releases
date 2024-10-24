from db.db_handler import DBHandler as DBH
from ext import logger
from db.query_builder import SelectQuery as Sel, UpdateQuery as Upd

class MusicDB(DBH):

    def __new__(cls, db_path):
        return super(MusicDB, cls).__new__(cls, db_path)
    
    def __parse_cols(self, columns):
        if isinstance(columns, list):
            return len(columns)
        elif columns == '*':
            return 0
        else:
            return len(columns.split(','))

    def __select_table(self, table, columns='*', condition=None):
        if self.__parse_cols(columns) == 1:
            return self.fetchsingle(table, columns, condition=condition)
        else:
            return self.fetchone(table, columns, condition=condition)

    def __get_artist(self, columns='*', condition=None):
        return self.__select_table('artists', columns, condition)
    
    def __get_release(self, columns='*', condition=None):
        return self.__select_table('releases', columns, condition)
    
    def __get_type(self, columns='*', condition=None):
        return self.__select_table('types', columns, condition)

    def get_artist_id(self, artist_name):
        return self.__get_artist('id', [{'condition': 'name = ?', 
                                        'params': (artist_name,)}])

    def get_artist_name(self, artist_id):
        return self.__get_artist('name', [{'condition': 'id = ?',
                                          'params': (artist_id,)}])
    
    def get_type_id(self, type_name):
        return self.__get_type('id', [{'condition': 'name = ?', 
                                      'params': (type_name,)}])

    def get_type_name(self, type_id):
        return self.__get_type('name', [{'condition': 'id = ?', 
                                        'params': (type_id,)}])

    def get_other_types(self, release_id):
        j = [{'table': 'types_releases', 
              'condition': 'types.id = types_releases.type_id'}]
        w = [{'condition': 'release_id = ?', 
              'params': (release_id,)}]
        
        return self.fetchone('types', 'name', j, w)
    
    def get_release_id(self, mbid):
        return self.__get_release('id', [{'condition': 'mbid = ?', 
                                         'params': (mbid,)}])
    
    def get_release_title(self, release_id):
        return self.__get_release('title', [{'condition': 'id = ?',
                                            'params': (release_id,)}])
    
    def get_releasing(self, keep_types=[], 
                     d_past=-1, d_fut=-1,
                     add_cols=None,
                     o_condition=None, order='ASC'):

        base_select = ['r.id', 'mbid', 'artist_mbid', 
                       'title', 'release_date', 't2.name']
        
        if keep_types:
            ft = [{'condition': f"t2.name IN ({', '.join(['?' for _ in keep_types])})",
                  'params': keep_types}]
            st = [{'condition': f"t.name IN ({', '.join(['?' for _ in keep_types])})",
                     'params': keep_types}]
        else:
            kt = []

        if add_cols:
            base_select += add_cols

        exq = Sel().select('1').table('types_releases').where('release_id = r.id')

        fq = Sel().select(base_select).table('releases', 'r')            

        fqj = [{'condition': 'r.primary_type = t2.id'}]
        fqj.extend(ft)
        fq.join('types', fqj, alias='t2')
        fq.where(f"NOT EXISTS ({exq.build()[0]})")

        sq = Sel().select(base_select).table('types_releases', 'tr')

        sqj = [{'condition': 'tr.type_id = t.id'}]
        sqj.extend(st)
        sq.join('types', sqj, alias='t')
        sq.join('releases', 'r.id = tr.release_id', alias='r')
        sq.join('types', 'r.primary_type = t2.id', alias='t2')

        fq.union(sq)

        qb = Sel().table(fq)

        if d_past != None and d_past >= 0:
            qb.where('release_date >= date("now", ?)', (f'-{d_past} days',))
        
        if d_fut != None and d_fut >= 0:
            qb.where('release_date <= date("now", ?)', (f'+{d_fut} days',))

        if o_condition:
            for cond in o_condition:
                qb.where(cond['condition'], cond.get('params', ()))

        qb.order_by(('release_date', 'title'), order)

        query, params = qb.build()
        logger.debug(query)
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

        """
        SELECT
            *
        FROM
            (
                SELECT
                    r.*,
                    t2.name AS name
                FROM
                    releases AS r
                    JOIN types AS t2 ON r.primary_type = t2.id
                    AND t2.name IN ('Album', 'Single', 'EP', 'Soundtrack')
                WHERE
                    NOT EXISTS (
                        SELECT
                            1
                        FROM
                            types_releases
                        WHERE
                            release_id = id
                    )
                UNION ALL
                SELECT
                    r.*,
                    t.name AS name
                FROM
                    types_releases AS tr
                    JOIN types AS t2 ON tr.type_id = t2.id
                    AND t2.name IN ('Album', 'Single', 'EP', 'Soundtrack')
                    JOIN releases AS r ON tr.release_id = r.id
                    JOIN types AS t ON r.primary_type = t.id
            )
        WHERE
            release_date >= date ('now', '-14 days')
            AND release_date <= date ('now', '+1 day')
            AND (
                last_notified IS NULL
                OR last_notified < date (release_date - '+2 days')
            )
        ORDER BY
            release_date,
            title ASC
        """

        if add_cols:
            base_select += add_cols
        
        qb = Sel().select(base_select)

        qb.table('releases', 'r')
        qb.join('types_releases', 'r.id = tr.release_id', 'LEFT', alias='tr')
        qb.join('types', 'tr.type_id = t.id', 'LEFT', alias='t')
        qb.join('types', 'r.primary_type = t2.id', alias='t2')

        if keep_types:
            qb.where(f"""(t.name IN ({", ".join(["?" for _ in keep_types])})
                        OR t.name ISNULL)""", keep_types)
        
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

        query, params = qb.build()
        logger.debug(query)
        logger.debug(params)
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
        '''
        SELECT
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
                t.name IN ('Album', 'Single', 'EP', 'Soundtrack')
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
