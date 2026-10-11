import os
from langchain.chat_models import init_chat_model
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain.agents import create_agent
from fastapi import Request

def vectorize(request: Request):
    hf = request.app.state.hug_model
    

def make_output(request: Request):
    gem = request.app.state.gem_model

