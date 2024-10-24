class QueryBuilder:
    def __init__(self):
        self._select = '*'
        self._table = ''
        self._join = []
        self._union = []
        self._where = []
        self._params = []
    
    def where(self, condition, params=()):
        self._where.append(condition)
        self._params.extend(params)
        return self
    
    def select(self, columns):
        if isinstance(columns, list):
            self._select = ', '.join(columns)
        else:
            self._select = columns
        return self
    
    def table(self, table, alias=None):
        if isinstance(table, SelectQuery):
            self._params.extend(table.get_params())
            table = f'({table.build()[0]})'
        alias_q = f' AS {alias}' if alias else ''

        self._table = f'{table} {alias_q}'
        return self
    
    def get_params(self):
        return self._params
    
    def build(self):
        raise NotImplementedError

class SelectQuery(QueryBuilder):
    def __init__(self):
        super().__init__()
        self._order_by = []
        self._order_by_dir = 'ASC'

    def join(self, table, conditions, join_type='INNER', alias=None):
        if isinstance(table, SelectQuery):
            self._params.extend(table.get_params())
            table = f'({table.build()[0]})'

        alias_q = f' AS {alias}' if alias else ''

        condition = []
        if isinstance(conditions, list):
            for c in conditions:
                condition.append(c.get('condition', ''))
                self._params.extend(c.get('params', ()))
        else:
            condition = [conditions]

        self._join.append(f'{join_type} JOIN ({table}) {alias_q} ON {' AND '.join(condition)}')
        return self
    
    def union(self, query):
        self._params.extend(query.get_params())
        self._union.append(f'UNION ALL {query.build()[0]}')
    
    #def join(self, table, condition, join_type='INNER'):
    #    self._join.append(f'{join_type} JOIN {table} ON {condition}')
    #    return self

    def order_by(self, columns, order='ASC'):
        self._order_by.extend(columns)
        self._order_by_dir = order
        return self
    
    def build(self, distinct=False):
        query = f"""SELECT {"" if not distinct else "DISTINCT"} 
                         {self._select} FROM {self._table}"""
        if self._join:
            query += ' ' + ' '.join(self._join)
        if self._where:
            query += ' WHERE ' + ' AND '.join(self._where)
        if self._order_by:
            query += ' ORDER BY ' + ', '.join(self._order_by) + ' ' + self._order_by_dir
        if self._union:
            query += ' ' + ' '.join(self._union)
        return query, self._params

class UpdateQuery(QueryBuilder):
    def __init__(self):
        super().__init__()
        self._values = []

    def set(self, columns, values=()):
        self._select = columns
        self._values.extend(values)
        return self

    def build(self):
        query = f'UPDATE {self._table} SET {", ".join([f"{c} = ?" for c in self._select])}'
        if self._where:
            query += ' WHERE ' + ' AND '.join(self._where)
        
        return query, self._values + self._params