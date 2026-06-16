import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid

load_dotenv()

# ── Config ──
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION = os.getenv("QDRANT_COLLECTION", "credito-demo")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))

# ── 1. Extraer texto del PDF ──
def extract_text(pdf_path: str) -> list[dict]:
    """Extrae texto página por página."""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append({
                "text": text.strip(),
                "page": i + 1,
                "source": os.path.basename(pdf_path)
            })
    doc.close()
    return pages


# ── 2. Limpiar texto ──
def clean_text(text: str) -> str:
    """Limpieza básica sin destruir semántica."""
    import re
    text = re.sub(r'[ \t]+', ' ', text)     # Solo espacios y tabulaciones múltiples -> uno
    text = re.sub(r'\n{2,}', '\n\n', text)  # Mantener saltos de párrafo/bloque
    text = text.strip()
    return text


CATEGORIES = [
    "TELEVISORES LED SMART TV",
    "ACONDICIONADORES DE AIRE SPLIT",
    "DESHUMIDIFICADORES",
    "REFRIGERADORES",
    "FREEZERS",
    "LAVADO Y SECADO",
    "COCINAS",
    "ANAFES",
    "HORNOS DE EMPOTRAR",
    "CAMPANAS EXTRACTORAS",
    "PURIFICADORES DE AIRE",
    "EXTRACTORES DE AIRE PARA BAÑO",
    "HORNOS ELÉCTRICOS",
    "HORNOS MICROONDAS",
    "ASPIRADORAS",
    "PEQUEÑOS ELECTRODOMÉSTICOS",
    "ESTUFAS",
    "VENTILADORES",
    "TERMOTANQUES",
    "PLANTA DE PRODUCCIÓN"
]

def extract_category(text: str) -> str:
    first_part = text[:300].upper()

    for cat in CATEGORIES:
        if cat in first_part:
            return cat

    return "UNKNOWN"


# ── 3. Chunking ──
def chunk_pages(pages: list[dict]) -> list[dict]:
    """Divide páginas en chunks manteniendo metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["Modelo", "\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    current_category = "UNKNOWN"

    for page in pages:
        cleaned = clean_text(page["text"])

        # Detectar si hay nueva categoría
        detected_category = extract_category(cleaned)
        if detected_category != "UNKNOWN":
            current_category = detected_category

        splits = splitter.split_text(cleaned)

        for split in splits:
            chunks.append({
                "text": split,
                "page": page["page"],
                "source": page["source"],
                "category": current_category
            })

    return chunks


# ── 4. Embeddings ──
def generate_embeddings(chunks: list[dict], model: SentenceTransformer) -> list[dict]:
    """Genera embeddings para cada chunk."""
    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts, show_progress_bar=True)

    for i, chunk in enumerate(chunks):
        chunk["vector"] = vectors[i].tolist()

    return chunks


# ── 5. Guardar en Qdrant ──
def store_in_qdrant(chunks: list[dict], force_recreate: bool = False):
    """Sube chunks con vectores a Qdrant."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    collections = [c.name for c in client.get_collections().collections]
    
    # Borrar colección vieja si existe y es primera ejecución
    if COLLECTION in collections and force_recreate:
        client.delete_collection(collection_name=COLLECTION)
        print(f"Colección '{COLLECTION}' eliminada.")
        collections = []

    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )
        print(f"Colección '{COLLECTION}' creada.")

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk["vector"],
            payload={
                "text": chunk["text"],
                "page": chunk["page"],
                "source": chunk["source"],
                "category": chunk["category"]
            }
        )
        for chunk in chunks
    ]

    client.upsert(collection_name=COLLECTION, points=points)
    print(f"{len(points)} chunks indexados en Qdrant.")


# ── Main ──
def main():
    pdf_dir = "data"
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]

    if not pdf_files:
        print("No se encontraron PDFs en /data")
        return

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    first = True  # borrar colección solo en el primer PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        print(f"\nProcesando: {pdf_path}")

        pages = extract_text(pdf_path)
        print(f"  Páginas extraídas: {len(pages)}")

        chunks = chunk_pages(pages)
        print(f"  Chunks generados: {len(chunks)}")

        print("  Generando embeddings...")
        chunks = generate_embeddings(chunks, model)

        store_in_qdrant(chunks, force_recreate=first)
        first = False

    print("\n✅ Ingesta completada para todos los PDFs.")

if __name__ == "__main__":
    main()