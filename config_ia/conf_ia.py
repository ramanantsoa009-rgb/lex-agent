import os
from dotenv import load_dotenv

load_dotenv()

class Config_IA:
    # liste import from dotenv / Parametres globaux
    MODEL_NAME: str = "ministral-3b-latest"
    TEMPERATURE: float = 0
    MAX_RETRIES: int = 3
    EMBEDDING_MODEL: str = "mistral-embed"
    TOP_K_RESULTS: int = 5

# exporter la classe Config
conf_ia = Config_IA()