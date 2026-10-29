"""Explicit additive migrations; importing this file does not start API services."""
import os
from alembic import context
from diagnostic.database import database_engine

from ecosystem.models import Base
from ecosystem.migration_policy import include_object

config = context.config
url = os.environ.get('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
if not url:
    raise RuntimeError('Set DATABASE_URL before running migrations')

if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True, compare_type=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = database_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True, include_object=include_object)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
