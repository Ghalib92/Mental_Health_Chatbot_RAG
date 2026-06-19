"""PDF loading, chunking and embedding helpers for the RAG pipeline."""

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_pdf_file(data):
    """Load every PDF in a directory into LangChain documents."""
    loader = DirectoryLoader(data, glob="*.pdf", loader_cls=PyPDFLoader)
    return loader.load()


def text_split(extracted_data):
    """Split documents into overlapping chunks suited to retrieval."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )
    return splitter.split_documents(extracted_data)


def download_hugging_face_embeddings():
    """384-dimension sentence-transformer embeddings (matches Pinecone index)."""
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
