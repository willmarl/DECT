from dotenv import load_dotenv
import os
from pydantic import SecretStr

load_dotenv()

# empty string added to avoid intellisense yelling

# LLM Settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

# Image model settings
IMAGE_MODEL_PROVIDER = os.getenv("IMAGE_MODEL_PROVIDER", "")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "")

# API keys & hosts
OPENAI_API_KEY = SecretStr(os.getenv("OPENAI_API_KEY", ""))
ANTHROPIC_API_KEY = SecretStr(os.getenv("ANTHROPIC_API_KEY", ""))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "")