from sqlalchemy import inspect, text
from src.config.database import Base, engine
from src import models
def migrate():
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        cols={t:{c['name'] for c in inspect(conn).get_columns(t)} for t in ['jobs','reports','deliveries']}
        for table,column,ddl in [('jobs','teams','teams JSON'),('reports','recipient_id','recipient_id INTEGER'),('deliveries','recipient_id','recipient_id INTEGER'),('deliveries','teams','teams JSON')]:
            if column not in cols.get(table,set()):
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {ddl}'))
if __name__=='__main__':migrate()
