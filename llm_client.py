from config import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_HOST,
    LLM_PROVIDER, LLM_MODEL,
    IMAGE_MODEL_PROVIDER, IMAGE_MODEL
)
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

# ============================================
# LLM FUNCTIONS
# ============================================

def get_llm():
    """
    Get the LLM based on provider and model from config
    
    Returns:
        LLM instance (ChatOpenAI, ChatAnthropic, or ChatOllama)
    """
    print(f"🤖 Initializing LLM: {LLM_PROVIDER} ({LLM_MODEL})")
    
    if LLM_PROVIDER == "openai":
        return ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY)
    elif LLM_PROVIDER == "anthropic":
        return ChatAnthropic(model_name=LLM_MODEL, api_key=ANTHROPIC_API_KEY, timeout=None, stop=None)
    elif LLM_PROVIDER == "ollama":
        return ChatOllama(model=LLM_MODEL, base_url=OLLAMA_HOST)
    else:
        raise ValueError(f"❌ Unknown provider: {LLM_PROVIDER}")

def get_image_llm():
    """
    Use multimodal LLM for image captioning
    
    Returns:
        Vision-capable LLM instance
    """
    print(f"👁️ Initializing vision LLM: {IMAGE_MODEL_PROVIDER} ({IMAGE_MODEL})")
    
    if IMAGE_MODEL_PROVIDER == "openai":
        return ChatOpenAI(model=IMAGE_MODEL, api_key=OPENAI_API_KEY)
    elif IMAGE_MODEL_PROVIDER == "anthropic":
        return ChatAnthropic(model_name=IMAGE_MODEL, api_key=ANTHROPIC_API_KEY, timeout=None, stop=None)
    elif IMAGE_MODEL_PROVIDER == "ollama":
        return ChatOllama(model=IMAGE_MODEL, base_url=OLLAMA_HOST)
    else:
        raise ValueError(f"❌ Unknown image model provider: {IMAGE_MODEL_PROVIDER}")