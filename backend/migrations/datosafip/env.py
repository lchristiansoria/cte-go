from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from ctg_go.modules.sisa.config import build_datosafip_url
from ctg_go.modules.sisa.models import DatosAfipBase

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = DatosAfipBase.metadata
VERSION_TABLE = "alembic_version_datosafip"


def _configure(**kwargs) -> None:
    context.configure(target_metadata=target_metadata, version_table=VERSION_TABLE, compare_type=True, **kwargs)


def run_migrations_offline() -> None:
    _configure(
        url=str(build_datosafip_url()), literal_binds=True, dialect_opts={"paramstyle": "named"}
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
        return
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = build_datosafip_url().render_as_string(hide_password=False)
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as conn:
        _configure(connection=conn)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
