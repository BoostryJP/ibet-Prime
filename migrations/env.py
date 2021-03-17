import sys
import re
from logging.config import fileConfig

from alembic.autogenerate import render
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from config import DATABASE_URL
from app.database import engine, get_db_schema
from app.model.db import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

schema = get_db_schema()


def _include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in [None, schema]
    else:
        return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"}
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    config_ini = config.get_section(config.config_ini_section)
    config_ini["sqlalchemy.url"] = DATABASE_URL
    connectable = engine_from_config(
        config_ini,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        include_schemas = False
        include_name = None
        if schema is not None:
            include_schemas = True
            include_name = _include_name
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            version_table_schema=get_db_schema(),
            include_schemas=include_schemas,
            include_name=include_name
        )

        with context.begin_transaction():
            context.run_migrations()


argv = sys.argv
if "--autogenerate" in argv:
    _render_op_org = getattr(render, "render_op")


    def render_op_wrapper(autogen_context, op):
        lines = _render_op_org(autogen_context, op)
        new_lines = []
        for line in lines:
            new_line = line
            if 'get_db_schema())' not in new_line:
                # Set schema of migration exec-environment
                if 'schema=' not in new_line:
                    new_line = re.sub('\)$', ', schema=get_db_schema())', line)
                else:  # If local environment has a schema set
                    new_line = re.sub('schema=(.|\s)*\)$', 'schema=get_db_schema())', line)
            new_lines.append(new_line)
        return new_lines


    setattr(render, "render_op", render_op_wrapper)

if "--sql" in argv:
    if schema is not None and engine.name == "postgresql":
        print(f"SET SEARCH_PATH TO {schema};")

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
