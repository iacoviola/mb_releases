class QueryBuilder:
    def __init__(self):
        self._select = '*'
        self._table = ''
        self._join = []
        self._where = []
        self._params = []
        self._order_by = []

    def join(self, table, condition, join_type='INNER'):
        self._join.append(f'{join_type} JOIN {table} ON {condition}')
        return self
    
    def where(self, condition, params=()):
        self._where.append(condition)
        self._params.extend(params)
        return self
    
    def order_by(self, column, order='ASC'):
        self._order_by.append(f'{column} {order}')
        return self
    
    def select(self, columns):
        if isinstance(columns, list):
            self._select = ', '.join(columns)
        else:
            self._select = columns
        return self
    
    def table(self, table):
        self._table = table
        return self
    
    def build(self, distinct=False):
        query = f'SELECT {"" if not distinct else "DISTINCT"} 
                         {self._select} FROM {self._table}'
        if self._join:
            query += ' ' + ' '.join(self._join)
        if self._where:
            query += ' WHERE ' + ' AND '.join(self._where)
        if self._order_by:
            query += ' ORDER BY ' + ', '.join(self._order_by)
        return query, self._params