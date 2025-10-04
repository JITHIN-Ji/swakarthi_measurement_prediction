import logging

# --- File Configuration ---
MEASUREMENTS_FILE = 'measurements.json'
MODEL_FILE = 'swakriti_body_predictor.pkl'

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)