"""Aplicación Celery (compose.prod ejecuta `celery -A ctg_go worker|beat`)."""
from __future__ import annotations

import os
from urllib.parse import quote

from celery import Celery
from celery.schedules import crontab

DEFAULT_CRON_SISA = "0 5 * * *"  # diario


def _broker_url() -> str:
    explicit = os.getenv("URL_BROKER")
    if explicit:
        return explicit
    user = quote(os.getenv("USR_RABBIT", "guest"), safe="")
    password = quote(os.getenv("PASS_RABBIT", "guest"), safe="")
    host = os.getenv("HOST_RABBIT", "localhost")
    port = os.getenv("PORT_RABBIT", "5672")
    vhost = quote(os.getenv("VHOST_RABBIT", "/"), safe="")
    return f"amqp://{user}:{password}@{host}:{port}/{vhost}"


def parse_cron(expresion: str) -> crontab:
    partes = (expresion or DEFAULT_CRON_SISA).split()
    if len(partes) != 5:
        raise ValueError("CRON_SISA debe tener 5 campos: minuto hora día-mes mes día-semana")
    minuto, hora, dia_mes, mes, dia_semana = partes
    return crontab(minute=minuto, hour=hora, day_of_month=dia_mes, month_of_year=mes, day_of_week=dia_semana)


app = Celery("ctg_go", broker=_broker_url())
app.conf.timezone = os.getenv("TZ_APP", "America/Argentina/Buenos_Aires")
app.conf.beat_schedule = {
    "sisa-sincronizar-padron": {
        "task": "ctg_go.sisa.sincronizar",
        "schedule": parse_cron(os.getenv("CRON_SISA", DEFAULT_CRON_SISA)),
    }
}


@app.task(name="ctg_go.sisa.sincronizar")
def sincronizar_sisa() -> dict:
    from ctg_go.modules.sisa.jobs import sincronizar_padron_sisa

    return sincronizar_padron_sisa("programada")
