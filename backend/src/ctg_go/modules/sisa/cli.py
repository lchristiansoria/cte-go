from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from ctg_go.modules.sisa.config import SisaConfig, build_datosafip_url, create_datosafip_engine
from ctg_go.modules.sisa.service import SisaEjecucionEnCurso, ejecutar_sincronizacion


def _alembic_config() -> Config:
    # migrations/datosafip/ vive junto al paquete en el repo y en la imagen (/app/migrations).
    base = Path(__file__).resolve()
    for parent in base.parents:
        candidato = parent / "migrations" / "datosafip" / "alembic.ini"
        if candidato.exists():
            config = Config(str(candidato))
            config.set_main_option("script_location", str(candidato.parent))
            return config
    raise RuntimeError("No se encontró migrations/datosafip/alembic.ini")


def crear_base() -> None:
    """Crea la base DatosAfip si no existe (requiere permiso CREATEDB; solo PostgreSQL)."""
    url = make_url(build_datosafip_url())
    nombre = url.database
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", future=True)
    with admin.connect() as conn:
        existe = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nombre})
        if not existe:
            conn.execute(text('CREATE DATABASE "' + nombre.replace('"', '""') + '"'))
            print(f"Base {nombre} creada")
        else:
            print(f"Base {nombre} ya existe")


def migrar() -> None:
    config = _alembic_config()
    engine = create_datosafip_engine()
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        connection.commit()
    print("Estructura DatosAfip actualizada")


def sincronizar(origen: str) -> int:
    resultado = ejecutar_sincronizacion(create_datosafip_engine(), SisaConfig.from_env(), origen=origen)
    print(json.dumps(
        {"ejecucion_id": resultado.ejecucion_id, "estado": resultado.estado, "motivo": resultado.motivo,
         "error": resultado.error, "metricas": resultado.metricas}, ensure_ascii=False))
    return 0 if resultado.estado == "completada" else 2


def estado(limite: int) -> int:
    from sqlalchemy import select

    from ctg_go.modules.sisa.models import Ejecucion

    engine = create_datosafip_engine()
    with engine.connect() as conn:
        filas = conn.execute(select(Ejecucion).order_by(Ejecucion.id.desc()).limit(limite)).mappings().all()
    for f in filas:
        print(json.dumps({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in f.items()},
                         ensure_ascii=False, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(prog="ctg-go-sisa", description="Padrón SISA local (base DatosAfip)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("crear-base", help="Crea la base DatosAfip si no existe")
    sub.add_parser("migrar", help="Crea/actualiza las tablas SISA_*")
    sync = sub.add_parser("sincronizar", help="Descarga y actualiza el padrón")
    sync.add_argument("--origen", default="manual", choices=["manual", "programada"])
    est = sub.add_parser("estado", help="Últimas ejecuciones")
    est.add_argument("--limite", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        if args.cmd == "crear-base":
            crear_base()
        elif args.cmd == "migrar":
            migrar()
        elif args.cmd == "sincronizar":
            return sincronizar(args.origen)
        elif args.cmd == "estado":
            return estado(args.limite)
    except SisaEjecucionEnCurso:
        print("Ya hay una ejecución SISA en curso", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
