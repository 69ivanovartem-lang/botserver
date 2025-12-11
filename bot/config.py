# config.py
import os
import logging
import structlog
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Настройка structlog
def setup_logging():
    """Настройка структурированного логирования"""
    # Преобразуем строковый уровень в числовой
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    # Настройка стандартного logging
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        handlers=[logging.StreamHandler()]
    )
    
    # Настройка structlog
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True
    )
    
    logger = structlog.get_logger()
    logger.info("logging_configured", log_level=LOG_LEVEL)
    return logger

# Инициализация логгера
logger = setup_logging()