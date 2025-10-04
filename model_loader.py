from joblib import load
from config import logger, MODEL_FILE

# Global variable to hold the loaded model
model = None

def initialize_model():
    """Load the pre-trained model into the global 'model' variable."""
    global model
    try:
        model = load(MODEL_FILE)
        logger.info(f"Pre-trained model '{MODEL_FILE}' loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        # In a production scenario, you might want the app to exit if the model fails to load.
        # raise e 