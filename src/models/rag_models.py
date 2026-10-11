import os
from langchain.chat_models import init_chat_model

# These models need to be loaded at startup
def get_gem_model():
    '''
    Model for producing RAG output
    '''
    gem_model = init_chat_model(
        "gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.2,
        max_tokens=1024,
        api_key=os.environ["GOOGLE_API_KEY"],
    )
    return gem_model

def get_hug_model():
    '''
    Model that makes embeddings to put in vector DB
    '''
    hug_model = init_chat_model(
        "microsoft/Phi-3-mini-4k-instruct",
        model_provider="huggingface",
        temperature=0.7,
        max_tokens=1023,
        api_key=os.environ["HUGGINGFACE_API_KEY"]
    )
    return hug_model