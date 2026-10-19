# logging_config.py
import logging
from config import configs

date_format = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt=date_format,
    handlers=[logging.FileHandler(configs.LOGS), logging.StreamHandler()],
)

logger = logging.getLogger()  # Obtén el objeto logger para su uso en otros módulos

# Configura el nivel de registro del logger de pika a ERROR
logging.getLogger("pika").setLevel(logging.ERROR)
