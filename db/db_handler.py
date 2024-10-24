import sqlite3
import logging

from db.query_builder import SelectQuery as Sel
from db.query_builder import UpdateQuery as Upd

logger = logging.getLogger(__name__)

class CONFLICT:
    IGNORE = 'IGNORE'
    REPLACE = 'REPLACE'
    ROLLBACK = 'ROLLBACK'
    ABORT = 'ABORT'
    FAIL = 'FAIL'

class STATUS:
    INSERT = 'INSERT'
    UPDATE = 'UPDATE'
    FAIL = 'FAIL'
    
class DBHandler:
    '''
    Class to handle core database operations
    '''

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
        qb = Sel().select(columns).table(table)
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
        return qb.build()

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
    
    def fetchsingle(self, table, column, joins=None, condition=None,
                    order_by=None):
        query, params = self._fetchbuild(table, 
                                         column, 
                                         joins, 
                                         condition,
                                         order_by)
        self.cursor.execute(query, params)
        r = self.cursor.fetchone()
        return r[0] if r else None
        
    def insert(self, table, columns=(), values=(), conflict=None):
        lc = len(columns)
        lv = len(values)

        if lc == 0:
            logger.debug('No columns provided, inserting all values')
        elif lc != lv:
            raise ValueError('Columns and values must have the same length')
        
        if not conflict:
            conflict = CONFLICT.FAIL

        query = f"""INSERT OR {conflict} INTO {table} 
                    {"" if not columns else "(" + ", ".join(columns) + ")"}
                         VALUES ({", ".join(["?" for _ in values])})"""

        logger.debug(query)

        self.cursor.execute(query, values)
        self.conn.commit()

        return self.cursor.lastrowid
    
    def insert_update(self, table, columns=(), values=(), conflict_columns=()):
        
        sel_val = []

        for i, c in enumerate(columns):
            if c in conflict_columns:
                sel_val.append(values[i])

        id = self.fetchall(table, ['id'], 
                           wheres=[{'condition': 
                                   ' AND '.join([f'{col} = ?' for col in conflict_columns]),
                                   'params': sel_val}])
        
        if id and len(id) > 0:
            self.update(table, columns, values, 
                        [{'condition': ' AND '.join([f'{col} = ?' for col in conflict_columns]),
                         'params': sel_val}])
            return id[0][0], STATUS.UPDATE
        else:
            self.insert(table, columns, values)
            return self.cursor.lastrowid, STATUS.INSERT
    
    def update(self, table, columns=(), values=(), condition=None):
        lc = len(columns)
        lv = len(values)

        if not condition:
            raise ValueError('No condition provided')

        if lc == 0:
            raise ValueError('Columns must have at least one element')
        
        if lc != lv:
            raise ValueError("Columns and values must have the same length: " + str(lc) + " != " + str(lv))
        
        q = Upd().table(table).set(columns, values)
        
        for where in condition:
            q.where(where['condition'], where['params'])

        query, params = q.build()

        logger.debug(query)

        self.cursor.execute(query, params)
        self.conn.commit()

    def delete(self, table, condition, params=()):
        query = f"DELETE FROM {table} WHERE {condition}"
        self.cursor.execute(query, params)
        self.conn.commit()