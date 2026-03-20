from alphaforge.data.db import init_db
from alphaforge.utils_config import load_config
from alphaforge.utils_logger import setup_logging

def bootstrap():
    setup_logging()
    c = load_config()
    init_db(c.db_path)
    return c
