from __future__ import annotations

import io
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ctg_go.modules.sisa import parser, service  # noqa: E402
from ctg_go.modules.sisa.config import SisaConfig  # noqa: E402
from ctg_go.modules.sisa.download import SisaDescargaError, extraer_txt  # noqa: E402
from ctg_go.modules.sisa.models import Actual, DatosAfipBase, Ejecucion, Historial, Temporal  # noqa: E402
from ctg_go.modules.sisa.queries import consultar_por_cuit  # noqa: E402

HEADER = (
    "Cuit;Razon Social /Denominacion;Estado de la CUIT;Fecha vigencia del Estado;"
    "Fecha notificacion DFE Estado ;CBU;Fecha Actualizacion CBU;Consumo Propio;Cod Categoria ;"
    "Categoria;Situacion Categoria;Fecha Vigencia Categoria;Fecha Notificacion DFE Categoria ;"
    "Observaciones;Fecha Generacion"
)
CBU = "0140312903665650657634"


def fila(cuit="20000000001", cod=1, razon="PEREZ NUÑO", estado=1, cbu=CBU, cat="PRODUCTOR", sit="AL",
         obs="", gen="01-NOV-26", consumo="NO"):
    cbu_fecha = "25/03/2022 16:35:53" if cbu else ""
    return (f"{cuit};{razon};{estado};02/10/2019;30/09/2019;{cbu};{cbu_fecha};{consumo};{cod};{cat};{sit};"
            f"02/10/2019;30/09/2019;{obs};{gen}")


def make_zip(lineas: list[str], *, meta="Fecha de Actualizacion :01/11/2026", name="RG_4310.txt") -> bytes:
    texto = "\n".join(([meta] if meta else []) + [HEADER] + lineas) + "\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name, texto.encode("cp1252"))
    return buf.getvalue()


def fetcher(contenido: bytes):
    def _fetch(config, destino: Path) -> None:
        destino.write_bytes(contenido)

    return _fetch


CFG = SisaConfig(min_filas=1, umbral_variacion_total_pct=50, umbral_ausentes_pct=50, umbral_modificadas_pct=80)


@pytest.fixture()
def engine(tmp_path):
    eng = create_engine(f"sqlite+pysqlite:///{tmp_path / 'datosafip.db'}", future=True)
    DatosAfipBase.metadata.create_all(eng)
    return eng


def correr(engine, lineas, cfg=CFG, **kw):
    return service.ejecutar_sincronizacion(engine, cfg, fetch=fetcher(make_zip(lineas, **kw)))


def actuales(engine):
    with Session(engine) as s:
        return {(r.cuit, r.cod_categoria): r for r in s.scalars(select(Actual))}


def contar(engine, modelo):
    with Session(engine) as s:
        return s.scalar(select(func.count()).select_from(modelo))


BASE = [fila("20000000001", 1), fila("20000000001", 8, cat="ARRENDADOR"), fila("20000000002", 1), fila("20000000003", 1)]


def test_primera_carga_y_multiples_categorias(engine):
    r = correr(engine, BASE)
    assert r.estado == "completada"
    assert r.metricas["filas_nuevas"] == 4
    assert contar(engine, Actual) == 4
    assert contar(engine, Historial) == 0
    assert contar(engine, Temporal) == 0
    with Session(engine) as s:
        consulta = consultar_por_cuit(s, "20-00000000-1")
        assert [c.cod_categoria for c in consulta.categorias] == [1, 8]
        assert consulta.razon_social == "PEREZ NUÑO"
        assert consulta.ultima_actualizacion is not None
        assert consultar_por_cuit(s, "20999999999").encontrado is False
        ej = s.get(Ejecucion, r.ejecucion_id)
        assert ej.filas_descargadas == 4 and len(ej.archivo_hash) == 64
        assert ej.archivo_codificacion == "cp1252" and ej.fecha_archivo.isoformat() == "2026-11-01"


def test_altas_modificaciones_ausencias(engine):
    correr(engine, BASE)
    r = correr(engine, [
        fila("20000000001", 1, razon="PEREZ NUEVO"),   # modificada
        fila("20000000001", 8, cat="ARRENDADOR"),       # sin cambios
        fila("20000000002", 1),                         # sin cambios
        fila("20000000004", 1),                         # alta (20000000003 ausente)
    ])
    assert r.estado == "completada", r.motivo
    assert (r.metricas["filas_nuevas"], r.metricas["filas_modificadas"],
            r.metricas["filas_ausentes"], r.metricas["filas_sin_cambios"]) == (1, 1, 1, 2)
    act = actuales(engine)
    assert set(act) == {("20000000001", 1), ("20000000001", 8), ("20000000002", 1), ("20000000004", 1)}
    assert act[("20000000001", 1)].razon_social == "PEREZ NUEVO"
    with Session(engine) as s:
        hist = {h.motivo_cierre: h for h in s.scalars(select(Historial))}
        assert set(hist) == {"modificacion", "ausencia"}
        assert hist["modificacion"].razon_social == "PEREZ NUÑO"
        assert hist["modificacion"].ejecucion_cierre_id == r.ejecucion_id
        assert hist["ausencia"].cuit == "20000000003"
        assert hist["ausencia"].vigente_hasta is not None


def test_fecha_generacion_no_genera_version_y_reproceso_es_idempotente(engine):
    correr(engine, BASE)
    r = correr(engine, [fila(l.split(";")[0], int(l.split(";")[8]), cat=l.split(";")[9], gen="02-NOV-26") for l in BASE])
    assert r.metricas["filas_sin_cambios"] == 4 and r.metricas["filas_modificadas"] == 0
    r = correr(engine, BASE)
    assert r.estado == "completada" and r.metricas["filas_sin_cambios"] == 4
    assert contar(engine, Actual) == 4 and contar(engine, Historial) == 0


def test_inactivos_y_bajas_se_conservan(engine):
    correr(engine, [fila(estado=0, sit="BA")])
    act = actuales(engine)[("20000000001", 1)]
    assert act.estado == 0 and act.situacion_categoria == "BA"


@pytest.mark.parametrize("linea,motivo", [
    (fila(cuit="2000"), "filas_rechazadas"),
    (fila(cuit="20000000077", estado=9), "filas_rechazadas"),
    ("a;b", "filas_rechazadas"),
])
def test_filas_invalidas_requieren_revision_y_preservan_padron(engine, linea, motivo):
    correr(engine, BASE)
    r = correr(engine, BASE + [linea])
    assert r.estado == "revision" and r.motivo == motivo
    assert contar(engine, Actual) == 4 and contar(engine, Historial) == 0
    with Session(engine) as s:
        ej = s.get(Ejecucion, r.ejecucion_id)
        assert ej.filas_rechazadas == 1 and ej.detalle["muestras_rechazo"]
        assert CBU not in str(ej.detalle)


def test_clave_duplicada_requiere_revision(engine):
    correr(engine, BASE)
    r = correr(engine, BASE + [fila("20000000002", 1, razon="OTRO")])
    assert r.estado == "revision" and r.metricas["filas_rechazadas"] == 2
    assert actuales(engine)[("20000000002", 1)].razon_social == "PEREZ NUÑO"


def test_archivo_vacio_y_encabezado_inesperado(engine):
    correr(engine, BASE)
    assert correr(engine, []).motivo == "archivo_vacio"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("RG_4310.txt", b"otra;cosa\n1;2\n")
    r = service.ejecutar_sincronizacion(engine, CFG, fetch=fetcher(buf.getvalue()))
    assert r.estado == "revision" and r.motivo == "encabezado_inesperado"
    assert contar(engine, Actual) == 4


def test_variacion_de_volumen_requiere_revision(engine):
    correr(engine, BASE)
    cfg = SisaConfig(min_filas=1, umbral_variacion_total_pct=20, umbral_ausentes_pct=90, umbral_modificadas_pct=90)
    r = correr(engine, BASE[:2], cfg)
    assert r.estado == "revision" and r.motivo == "variacion_volumen"
    assert contar(engine, Actual) == 4
    r = correr(engine, BASE, SisaConfig(min_filas=10))
    assert r.motivo == "volumen_minimo"


def test_rollback_ante_error_preserva_padron(engine, monkeypatch):
    correr(engine, BASE)

    def boom(*a, **k):
        raise RuntimeError("falla simulada " + CBU)

    monkeypatch.setattr(service, "_insertar_nuevas_versiones", boom)
    r = correr(engine, [fila("20000000001", 1, razon="CAMBIO")] + BASE[1:] + [fila("20000000009", 1)])
    assert r.estado == "fallida" and CBU not in (r.error or "")
    act = actuales(engine)
    assert len(act) == 4 and act[("20000000001", 1)].razon_social == "PEREZ NUÑO"
    assert contar(engine, Historial) == 0


def test_ejecucion_simultanea_bloqueada_y_vencida_reemplazada(engine):
    ahora = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(Ejecucion.__table__.insert().values(estado="en_curso", origen="manual", inicio=ahora))
    with pytest.raises(service.SisaEjecucionEnCurso):
        correr(engine, BASE)
    with engine.begin() as conn:
        conn.execute(Ejecucion.__table__.update().values(inicio=datetime(2020, 1, 1, tzinfo=timezone.utc)))
    assert correr(engine, BASE).estado == "completada"


def test_extraccion_zip_segura(tmp_path):
    cfg = SisaConfig()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.txt", b"x")
    z = tmp_path / "a.zip"
    z.write_bytes(buf.getvalue())
    with pytest.raises(SisaDescargaError):
        extraer_txt(z, tmp_path, cfg)
    z.write_bytes(b"<html>no zip</html>")
    with pytest.raises(SisaDescargaError):
        extraer_txt(z, tmp_path, cfg)
    z.write_bytes(make_zip(BASE, name="sub/RG4310.txt"))
    assert extraer_txt(z, tmp_path, cfg).name == "padron_sisa.txt"


def test_parser_formato_real():
    reg, errores = parser.parsear_linea(
        "20004644493;SUCESION DE PETRONI;0;19/10/2023;17/10/2023;;;NO;1;PRODUCTOR ;BA;19/10/2023;17/10/2023;;01-NOV-26")
    assert errores == [] and reg["cbu"] is None and reg["fecha_actualizacion_cbu"] is None
    assert reg["categoria"] == "PRODUCTOR" and reg["fecha_generacion"].isoformat() == "2026-11-01"
    assert reg["observaciones"] is None


def test_migracion_datosafip_crea_tablas(tmp_path):
    root = Path(__file__).resolve().parents[1] / "migrations" / "datosafip"
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root))
    eng = create_engine(f"sqlite+pysqlite:///{tmp_path / 'm.db'}", future=True)
    with eng.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
        conn.commit()
        insp = inspect(conn)
        assert {"SISA_Actual", "SISA_Historial", "SISA_Temporal", "SISA_Ejecuciones"} <= set(insp.get_table_names())
        assert insp.get_pk_constraint("SISA_Actual")["constrained_columns"] == ["cuit", "cod_categoria"]
