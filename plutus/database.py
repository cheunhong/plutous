from sqlmodel.sql.expression import Select, SelectOfScalar
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, create_engine, text
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command
from typing import Optional
from .config import config
from .models import *
import logging
import os


logger = logging.getLogger(__name__)

db = config['db']
def get_uri(
    host: Optional[str] = db['host'],
    port: Optional[str] = db['port'],
    user: Optional[str] = db['user'],
    password: Optional[str] = db['password'],
    database: Optional[str] = db['database'],
    driver: Optional[str] = 'pymysql',
) -> str:
    return f"mysql+{driver}://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(get_uri())
async_engine = create_async_engine(get_uri(driver='asyncmy'))
is_engine = create_engine(get_uri(database='information_schema')
)
Session = sessionmaker(engine, autoflush=False)

# Silencing some SQL Alchemy warning about inherit_cache performance
SelectOfScalar.inherit_cache = True  # type: ignore
Select.inherit_cache = True  # type: ignore


def _get_alembic_config():
    current_dir = os.path.dirname(__file__)
    directory = os.path.join(current_dir, 'migrations')
    config = Config(os.path.join(current_dir, 'alembic.ini'))
    config.set_main_option('script_location', directory)
    config.set_main_option('sqlalchemy.url', get_uri())

    return config


def init():
    """
    Create all models under specified schema, and stamp the latest alembic version.
    Will skip if tables already existed in that schema.
    """
    sql = f"""
        SELECT EXISTS(
            SELECT *
            FROM TABLES
            WHERE TABLE_SCHEMA = '{db}'
            LIMIT 1
        )
    """
    with is_engine.connect() as conn:
        exists = conn.execute(text(sql)).one()[0]
        if exists:
            logger.warning(f'Database {db} already contains table, Skipping...')
            return

    SQLModel.metadata.create_all(engine)
    alembic_cfg = _get_alembic_config()
    command.stamp(alembic_cfg, "head")


def revision(msg: str, **kwargs):
    alembic_cfg = _get_alembic_config()
    command.revision(alembic_cfg, message=msg, autogenerate=True, **kwargs)


def upgrade(revision: str = 'head', **kwargs):
    alembic_cfg = _get_alembic_config()
    command.upgrade(alembic_cfg, revision, **kwargs)


def downgrade(revision: str, **kwargs):
    alembic_cfg = _get_alembic_config()
    command.downgrade(alembic_cfg, revision, **kwargs)