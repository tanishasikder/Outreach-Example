'''
Loads the sales PDFs into the Qdrant vector DB used by the RAG report.
Qdrant Cloud Inference turns the text into embeddings, so no embedding
model runs locally. Run from the project root (rebuilds the collection):
    python -m src.models.vector
'''

from pathlib import Path
import os

from src.core.config import load_env
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Document

load_env()

BASE_DIR = Path(__file__).resolve().parents[2]

COLLECTION = 'sales_example'
EMBED_MODEL = 'sentence-transformers/all-minilm-l6-v2' # Hosted by Qdrant Cloud (free)
EMBED_DIM = 384                                        # must match the model
PDFS = [
    'data/B2B Sales Process Handbook 2021.pdf',
    'data/sales-pipeline-course.pdf',
]

def get_client() -> QdrantClient:
    # connect to Qdrant Cloud
    url, key = os.environ.get('QDRANT_URL'), os.environ.get('QDRANT_KEY')
    if not url or not key:
        raise RuntimeError('QDRANT_URL and QDRANT_KEY must be set in .env')
    return QdrantClient(url=url, api_key=key, cloud_inference=True)

def load_chunks(pdf_list) -> list[dict]: # List of PDF paths to add to db
    splits = RecursiveCharacterTextSplitter(
        chunk_size=2500,
        chunk_overlap=300
    )
    chunks = []
    for file in pdf_list:
        # Extract all text from the pdf, then split it
        reader = PdfReader(BASE_DIR / file)
        text = '\n'.join(p.extract_text() or '' for p in reader.pages)
        for chunk in splits.split_text(text):
            chunks.append({'text': chunk, 'source': Path(file).name})
    return chunks

def create_collect(client: QdrantClient, recreate: bool = True):
    if recreate and client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION) # Start clean so old chunks don't linger
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )

def store_vector(client: QdrantClient, chunks: list[dict], batch_size: int = 64):
    points = [
        PointStruct(
            id=i,
            vector=Document(text=chunk['text'], model=EMBED_MODEL), # Embedded by Qdrant
            payload={**chunk, 'chunk_id': i}
        )
        for i, chunk in enumerate(chunks)
    ]
    for start in range(0, len(points), batch_size):
        client.upsert(collection_name=COLLECTION, points=points[start:start + batch_size])

if __name__ == '__main__':
    chunks = load_chunks(PDFS)
    client = get_client()
    create_collect(client)
    store_vector(client, chunks)
    print(f'Stored {len(chunks)} chunks in "{COLLECTION}"')
