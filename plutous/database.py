from plutous.config import config
from plutous.models import *

from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlmodel.sql.expression import Select, SelectOfScalar
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import URL
from sqlmodel import SQLModel, create_engine, text
from alembic.config import Config
from alembic import command

import logging
import os


logger = logging.getLogger(__name__)

db = config['db']
uri = URL.create(**db)

engine = create_engine(uri)
async_engine = create_async_engine(uri.set(driver='asyncmy'))
is_engine = create_engine(uri.set(database='information_schema'))
Session = sessionmaker(engine, autoflush=False)
AsyncSession = sessionmaker(async_engine, autoflush=False, class_=_AsyncSession)

# Silencing some SQL Alchemy warning about inherit_cache performance
SelectOfScalar.inherit_cache = True  # type: ignore
Select.inherit_cache = True  # type: ignore


def _get_alembic_config():
    current_dir = os.path.dirname(__file__)
    directory = os.path.join(current_dir, 'migrations')
    config = Config(os.path.join(current_dir, 'alembic.ini'))
    config.set_main_option('script_location', directory)
    config.set_main_option('sqlalchemy.url', uri)
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