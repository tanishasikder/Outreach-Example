import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

# Embeddings are made by Qdrant Cloud Inference (see src/models/vector.py),
# so the only model the app loads itself is the LLM that writes the report
def get_gem_model():
    '''
    Model for producing RAG output
    '''
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set in .env")
    gem_model = init_chat_model(
        "gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.2,
        max_tokens=2048,
        thinking_budget=0, # Gemini 2.5 "thinking" uses the same token budget and can leave the answer empty
        api_key=api_key,
    )
    return gem_model
