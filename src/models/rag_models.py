import os
from src.core.config import load_env
from langchain.chat_models import init_chat_model

load_env()

# Embeddings are made by Qdrant Cloud Inference (see src/models/vector.py),
# so the only model the app loads itself is the LLM that writes the report
def get_llm():
    '''
    Model for producing RAG output (Groq)
    '''
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set in .env")
    llm = init_chat_model(
        "llama-3.3-70b-versatile",
        model_provider="groq",
        temperature=0.2,
        max_tokens=2048,
        api_key=api_key,
    )
    return llm
