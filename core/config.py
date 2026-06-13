import os
from dotenv import load_dotenv
from loguru import logger
import sys

load_dotenv()


logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> - {message}")
logger.add("logs/mantlemind.log", rotation="10 MB", retention="7 days", level="DEBUG")

MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
MANTLE_CHAIN_ID = int(os.getenv("MANTLE_CHAIN_ID", 5000))


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


WHALE_THRESHOLD_MNT = float(os.getenv("WHALE_THRESHOLD_MNT", 100000))
ALPHA_ALERT_THRESHOLD = int(os.getenv("ALPHA_ALERT_THRESHOLD", 75))
ANOMALY_ALERT_THRESHOLD = float(os.getenv("ANOMALY_ALERT_THRESHOLD", 0.7))


REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports/")
DATA_CACHE_FILE = "data/tx_cache.csv"
ALERT_HISTORY_FILE = "data/alert_history.json"
MODEL_CACHE_FILE = "data/iso_forest_model.pkl"

os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)


ISO_FOREST_CONTAMINATION = 0.05
ISO_FOREST_N_ESTIMATORS = 200
FEATURE_WINDOW = 50          
BLOCKS_PER_FETCH = 20        

MNT_DECIMALS = 18
WEI_TO_MNT = 10 ** MNT_DECIMALS
