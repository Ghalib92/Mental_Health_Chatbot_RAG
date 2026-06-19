"""
One-off ingestion: load the mental-health PDFs in Data/, chunk and embed them,
and upsert into a Pinecone index. Run once before using the chatbot:

    python store_index.py
"""

import os

from dotenv import load_dotenv
from pinecone import ServerlessSpec
from pinecone.grpc import PineconeGRPC as Pinecone
from langchain_pinecone import PineconeVectorStore

from src.helper import download_hugging_face_embeddings, load_pdf_file, text_split

load_dotenv()

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "mentalbot")

extracted_data = load_pdf_file(data="Data/")
text_chunks = text_split(extracted_data)
embeddings = download_hugging_face_embeddings()

pc = Pinecone(api_key=PINECONE_API_KEY)

if not pc.has_index(INDEX_NAME):
    pc.create_index(
        name=INDEX_NAME,
        dimension=384,  # all-MiniLM-L6-v2 output dimension
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

PineconeVectorStore.from_documents(
    documents=text_chunks,
    index_name=INDEX_NAME,
    embedding=embeddings,
)

print(f"Indexed {len(text_chunks)} chunks into Pinecone index '{INDEX_NAME}'.")
