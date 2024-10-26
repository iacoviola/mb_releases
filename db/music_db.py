import logging

from db.db_handler import DBHandler as DBH
from db.query_builder import SelectQuery as Sel, UpdateQuery as Upd

logger = logging.getLogger(__name__)

class MusicDB(DBH):
    '''
    Extension of the DBHandler class to handle db operations specific to mb_releases
    '''

    def __new__(cls, db_path: str):
        '''
        Singleton pattern to ensure only one instance of the class is created

        Parameters:
            db_path (str): Database file path

        Returns:
            MusicDB: Instance of the class
        '''

        return super(MusicDB, cls).__new__(cls, db_path)
    
    def __parse_cols(self, columns: str | list) -> int:
        '''
        Returns the number of columns to select

        Parameters:
            columns (str | list): The columns to select

        Returns:
            int: The number of columns to select (0 if all columns)
        '''
        
        if isinstance(columns, list):
            return len(columns)
        elif columns == '*':
            return 0
        else:
            return len(columns.split(','))

    def __select_table(self, table, columns='*', condition=[]) -> any:
        '''
        Auxiliary method to select a table, it can return a single column
        or a set of columns

        Parameters:
            table (str): The table to select
            columns (str): The columns to select
            condition (list): The condition to apply

        Returns:
            set: The set of columns for the selected table (multiple columns)
            None: If no values are found
            any: The value of the selected column (single column)
        '''

        if self.__parse_cols(columns) == 1:
            return self.fetchsingle(table, columns, condition=condition)
        else:
            return self.fetchone(table, columns, condition=condition)

    def __get_artist(self, columns='*', condition=[]) -> any:
        '''
        Auxiliary method to select an artist

        Parameters:
            columns (str): The columns to select
            condition (list): The condition to apply

        Returns:
            set: The set of columns for the selected artist (multiple columns)
            None: If no artists are found
            any: The value of the selected column (single column)
        '''

        return self.__select_table('artists', columns, condition)
    
    def __get_release(self, columns='*', condition=[]) -> any:
        '''
        Auxiliary method to select a release

        Parameters:
            columns (str): The columns to select
            condition (list): The condition to apply

        Returns:
            set: The set of columns for the selected release (multiple columns)
            None: If no releases are found
            any: The value of the selected column (single column)
        '''

        return self.__select_table('releases', columns, condition)
    
    def __get_type(self, columns='*', condition=[]) -> any:
        '''
        Auxiliary method to select a type

        Parameters:
            columns (str): The columns to select
            condition (list): The condition to apply

        Returns:
            set: The set of columns for the selected type (multiple columns)
            None: If no types are found
            any: The value of the selected column (single column)
        '''
        
        return self.__select_table('types', columns, condition)

    def get_artist_id(self, a_name: str) -> int | None:
        '''
        Gets the ID of an artist by its name

        Parameters:
            artist_name (str): The name of the artist

        Returns:
            int: The ID of the artist
            None: If the artist is not found
        '''
        
        return self.__get_artist('id', [{'condition': 'name = ?', 
                                        'params': (a_name,)}])

    def get_artist_name(self, a_id: int) -> str | None:
        '''
        Gets the name of an artist by its ID

        Parameters:
            a_id (int): The ID of the artist

        Returns:
            str: The name of the artist
            None: If the artist is not found
        '''

        return self.__get_artist('name', [{'condition': 'id = ?',
                                          'params': (a_id,)}])
    
    def get_type_id(self, t_name: str) -> int | None:
        '''
        Gets the ID of a type by its name

        Parameters:
            t_name (str): The name of the type

        Returns:
            int: The ID of the type
            None: If the type is not found
        '''
        
        return self.__get_type('id', [{'condition': 'name = ?', 
                                      'params': (t_name,)}])

    def get_type_name(self, t_id: int) -> str | None:
        '''
        Gets the name of a type by its ID
        
        Parameters:
            t_id (int): The ID of the type

        Returns:
            str: The name of the type
            None: If the type is not found
        '''
        
        return self.__get_type('name', [{'condition': 'id = ?', 
                                        'params': (t_id,)}])

    def get_other_types(self, r_id) -> list | None:
        '''
        Gets the secondary types of a release

        Parameters:
            r_id (int): The ID of the release

        Returns:
            list: The list of secondary types
            None: If no secondary types are found
        '''
        
        j = [{'table': 'types_releases', 
              'condition': 'types.id = types_releases.type_id'}]
        w = [{'condition': 'release_id = ?', 
              'params': (r_id,)}]
        
        return self.fetchone('types', 'name', j, w)
    
    def get_release_id(self, r_mbid: str) -> int | None:
        '''
        Gets the ID of a release by its name

        Parameters:
            r_mbid (str): The MBID of the release

        Returns:
            int: The ID of the release
            None: If the release is not found
        '''

        return self.__get_release('id', [{'condition': 'mbid = ?', 
                                         'params': (r_mbid,)}])
    
    def get_release_title(self, r_id: int) -> str | None:
        '''
        Gets the title of a release by its ID

        Parameters:
            r_id (int): The ID of the release

        Returns:
            str: The title of the release
            None: If the release is not found
        '''

        return self.__get_release('title', [{'condition': 'id = ?',
                                            'params': (r_id,)}])
    
    def get_releasing(self, keep_types: list = [], 
                     d_past: int = -1, d_fut: int = -1,
                     add_cols: list = [],
                     o_condition: list = [], order: str = 'ASC') -> list | None:
        
        '''
        Executes a query to get interesting releases.

        Parameters:
            keep_types (list): The types of releases to select
            d_past (int): Number of days in the past to generate
            d_fut (int): Number of days in the future to generate
            add_cols (list): Additional columns to select
            o_condition (list): Other conditions to apply

        Returns:
            list: The list of interesting releases
            None: If no releases are found
        '''

        base_select = ['r.id', 'mbid', 'artist_mbid', 
                       'title', 'release_date', 't2.name']
        
        kt_str = ', '.join(['?' for _ in keep_types])

        base_select += add_cols

        exq = Sel().select('1').table('types_releases').where('release_id = r.id')

        fq = Sel().select(base_select).table('releases', 'r')            

        fqj = [{'condition': 'r.primary_type = t2.id'}]
        fqj.append({'condition': f"t2.name IN ({kt_str})", 'params': keep_types})

        fq.join('types', fqj, alias='t2')
        fq.where(f"NOT EXISTS ({exq.build()[0]})")

        sq = Sel().select(base_select).table('types_releases', 'tr')

        sqj = [{'condition': 'tr.type_id = t.id'}]
        sqj.append({'condition': f"t.name IN ({kt_str})", 'params': keep_types})
        
        sq.join('types', sqj, alias='t')
        sq.join('releases', 'r.id = tr.release_id', alias='r')
        sq.join('types', 'r.primary_type = t2.id', alias='t2')

        fq.union(sq)

        qb = Sel().table(fq)

        if d_past != None and d_past >= 0:
            qb.where('release_date >= date("now", ?)', (f'-{d_past} days',))
        
        if d_fut != None and d_fut >= 0:
            qb.where('release_date <= date("now", ?)', (f'+{d_fut} days',))

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