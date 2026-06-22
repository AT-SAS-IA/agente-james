import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid
import re
import json

load_dotenv()

# ── Config ──
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION = os.getenv("QDRANT_COLLECTION", "credito-demo")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))

# ── 1. Extraer texto del PDF con Coordenadas y Layout ──
def extract_page_zones_layout_aware(page, physical_page_num: int, source_name: str) -> list[dict]:
    """Extrae bloques de texto con coordenadas, los separa en columnas izquierda/derecha y los ordena visualmente."""
    blocks = page.get_text("blocks")
    rect = page.rect
    width = rect.width
    mid = width / 2
    is_double = width > 700

    left_blocks = []
    right_blocks = []

    for b in blocks:
        # b = (x0, y0, x1, y1, text, block_no, block_type)
        x0, y0, x1, y1, text, block_no, block_type = b
        if block_type != 0:  # omitir no-texto (imágenes, etc)
            continue
            
        block_center_x = (x0 + x1) / 2
        if is_double:
            if block_center_x < mid:
                left_blocks.append(b)
            else:
                right_blocks.append(b)
        else:
            left_blocks.append(b)

    # Ordenar bloques en cada zona de arriba a abajo, izquierda a derecha
    # Redondeamos y0 a múltiplos de 5 puntos para agrupar líneas que están al mismo nivel horizontal
    def sort_key(b):
        x0, y0, x1, y1, text, block_no, block_type = b
        return (round(y0 / 5) * 5, x0)

    left_blocks.sort(key=sort_key)
    right_blocks.sort(key=sort_key)

    left_text = clean_text("\n".join([b[4] for b in left_blocks]))
    right_text = clean_text("\n".join([b[4] for b in right_blocks]))

    zones = []
    if is_double:
        left_page_num = max(0, 2 * physical_page_num - 4)
        right_page_num = 2 * physical_page_num - 3
        if left_text:
            zones.append({"page": left_page_num, "text": left_text, "source": source_name})
        if right_text:
            zones.append({"page": right_page_num, "text": right_text, "source": source_name})
    else:
        page_num = physical_page_num if physical_page_num == 1 else (2 * physical_page_num - 4)
        if left_text:
            zones.append({"page": page_num, "text": left_text, "source": source_name})

    return zones


def extract_text(pdf_path: str) -> list[dict]:
    """Extrae texto página por página, dividiendo pliegos dobles verticalmente con orden visual."""
    doc = fitz.open(pdf_path)
    pages = []
    source_name = os.path.basename(pdf_path)
    for i, page in enumerate(doc, start=1):
        zones = extract_page_zones_layout_aware(page, i, source_name)
        pages.extend(zones)
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


def extract_category_by_page(page_num: int, chunk_text: str) -> str:
    """Retorna la categoría en mayúsculas exacta para app.py según la página lógica."""
    if 2 <= page_num <= 3:
        return "TELEVISORES LED SMART TV"
    elif page_num == 4:
        return "ACONDICIONADORES DE AIRE SPLIT"
    elif page_num == 5:
        return "DESHUMIDIFICADORES"
    elif (6 <= page_num <= 14) or (16 <= page_num <= 23) or (26 <= page_num <= 27):
        return "REFRIGERADORES"
    elif page_num == 15 or (24 <= page_num <= 25):
        return "FREEZERS"
    elif 28 <= page_num <= 35:
        return "LAVADO Y SECADO"
    elif 36 <= page_num <= 37:
        return "LAVAVAJILLAS"
    elif 38 <= page_num <= 49:
        return "COCINAS"
    elif 50 <= page_num <= 52:
        return "ANAFES"
    elif page_num == 53:
        return "HORNOS DE EMPOTRAR"
    elif 54 <= page_num <= 57:
        return "CAMPANAS EXTRACTORAS"
    elif page_num == 58:
        return "PURIFICADORES DE AIRE"
    elif page_num == 59:
        return "EXTRACTORES DE AIRE PARA BAÑO"
    elif 60 <= page_num <= 61:
        return "HORNOS ELÉCTRICOS"
    elif 62 <= page_num <= 65:
        return "HORNOS MICROONDAS"
    elif 66 <= page_num <= 67:
        return "ASPIRADORAS"
    elif 68 <= page_num <= 73:
        return "PEQUEÑOS ELECTRODOMÉSTICOS"
    elif 74 <= page_num <= 79:
        return "ESTUFAS"
    elif 80 <= page_num <= 83:
        return "VENTILADORES"
    elif 84 <= page_num <= 85:
        return "TERMOTANQUES"
    elif page_num == 88 or page_num == 89:
        return "PLANTA DE PRODUCCIÓN"
    else:
        return "NINGUNA"


# ── 3. Chunking ──
def chunk_pages(pages: list[dict]) -> list[dict]:
    """Divide páginas en chunks manteniendo metadata y asignando categorías correctas con contexto."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["Modelo", "\n\n", "\n", ". ", " ", ""]
    )

    chunks = []

    for page in pages:
        cleaned = clean_text(page["text"])
        
        # Extraer el encabezado de la página (todo antes del primer "Modelo")
        header_match = re.split(r'\b(?:Modelo|MODELO)\b', cleaned, maxsplit=1)
        page_header = ""
        if len(header_match) > 1:
            page_header = header_match[0].strip()
            # Limitar el tamaño del header a 300 caracteres para evitar inflar el chunk
            if len(page_header) > 300:
                page_header = page_header[:297] + "..."
        
        splits = splitter.split_text(cleaned)

        for split in splits:
            category = extract_category_by_page(page["page"], split)
            
            # Re-inyectar contexto a la porción de texto del producto
            chunk_text = split
            if (split.strip().startswith(("Modelo", "MODELO")) or "Modelo " in split) and page_header:
                if page_header not in split:
                    chunk_text = f"{page_header}\n\n{split}"
            
            # Prepend de categoría como ancla de metadatos semánticos
            chunk_text = f"Categoría: {category}\n{chunk_text}"

            chunks.append({
                "text": chunk_text,
                "page": page["page"],
                "source": page["source"],
                "category": category
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
    client = QdrantClient(path="./qdrant_db")

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


def get_page_headers(pdf_path: str) -> dict[int, str]:
    """Extrae el texto inicial (antes del primer 'Modelo') de cada página lógica usando extract_text."""
    pages = extract_text(pdf_path)
    page_headers = {}
    for pg in pages:
        text = pg["text"]
        header_match = re.split(r'\b(?:Modelo|MODELO)\b', text, maxsplit=1)
        header = header_match[0].strip() if header_match else ""
        if len(header) > 300:
            header = header[:297] + "..."
        page_headers[pg["page"]] = header
    return page_headers


def format_product_chunk(p: dict, page_header: str = "") -> str:
    """Crea una descripción textual muy rica y legible para indexar el producto en Qdrant."""
    parts = []
    
    # 1. Categoría y Subcategoría
    cat_line = f"JAMES - Categoría: {p['category'].upper()}"
    if p.get('subcategory'):
        cat_line += f" ({p['subcategory']})"
    parts.append(cat_line)
    
    # 2. Contexto de página (contiene términos clave como "FRIGOBAR")
    if page_header:
        parts.append(f"Contexto del Catálogo: {page_header}")
        
    # 3. Modelo y Color
    model_line = f"Modelo: {p['model']}"
    if p.get('color'):
        model_line += f" - Color: {p['color']}"
    parts.append(model_line)
    
    # 4. Dimensiones
    dims = p.get('dimensions_mm') or {}
    if dims.get('width') or dims.get('depth') or dims.get('height'):
        parts.append(f"Dimensiones: Ancho {dims.get('width')} mm x Profundidad {dims.get('depth')} mm x Altura {dims.get('height')} mm")
        
    # 5. Dimensiones de instalación
    inst = p.get('installation_dimensions_mm') or {}
    if inst.get('width') or inst.get('depth') or inst.get('height'):
        parts.append(f"Dimensiones de instalación: Ancho {inst.get('width')} mm x Profundidad {inst.get('depth')} mm x Altura {inst.get('height')} mm")
        
    # 6. Eficiencia energética
    if p.get('energy_rating'):
        parts.append(f"Eficiencia energética: {p['energy_rating']}")
        
    # 7. Especificaciones
    specs = p.get('specs') or {}
    if specs:
        specs_list = []
        for k, v in specs.items():
            name = k.replace('_', ' ').replace('L', 'litros').replace('kg', 'kg').title()
            specs_list.append(f"{name}: {v}")
        parts.append("Especificaciones: " + " · ".join(specs_list))
        
    # 8. Características
    feats = p.get('features') or []
    if feats:
        parts.append("Características: " + " · ".join(feats))
        
    # 9. Página
    parts.append(f"Fuente del Catálogo: Página {p['source_page']}")
    
    return "\n".join(parts)


# ── Main ──
def main():
    pdf_dir = "data"
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]

    if not pdf_files:
        print("No se encontraron PDFs en /data")
        return

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    # Cargar los productos estructurados del JSON
    json_path = "catalogo_james_productos.json"
    products = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                products = json.load(f)
            print(f"Cargados {len(products)} productos estructurados desde {json_path}")
        except Exception as e:
            print(f"Error al cargar {json_path}: {e}")
    else:
        print(f"⚠️ ADVERTENCIA: No se encontró '{json_path}' en el directorio de trabajo ({os.getcwd()}).")
        print("Por favor, asegúrate de correr 'docker compose build' para empaquetar el JSON actualizado en la imagen de Docker antes de correr la ingesta.")
            
    first = True
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        print(f"\nProcesando: {pdf_path}")
        
        # 1. Obtener headers de todas las páginas lógicas para contextualizar los productos
        page_headers = get_page_headers(pdf_path)
        
        chunks = []
        product_pages = set()
        
        # 2. Agregar chunks estructurados para los productos
        for p in products:
            p_page = p.get("source_page")
            product_pages.add(p_page)
            
            p_header = page_headers.get(p_page, "")
            formatted_text = format_product_chunk(p, p_header)
            
            category = extract_category_by_page(p_page, p.get("raw_text", ""))
            
            chunks.append({
                "text": formatted_text,
                "page": p_page,
                "source": p.get("source") or pdf_file,
                "category": category
            })
            
        print(f"  Generados {len(chunks)} chunks estructurados para productos.")
        
        # 3. Extraer páginas del PDF que NO tienen productos asociados (ej: showroom, service, etc.)
        all_pages = extract_text(pdf_path)
        general_pages = [pg for pg in all_pages if pg["page"] not in product_pages]
        print(f"  Páginas generales sin productos (como showroom/service): {[pg['page'] for pg in general_pages]}")
        
        general_chunks = chunk_pages(general_pages)
        print(f"  Generados {len(general_chunks)} chunks para páginas generales.")
        
        chunks.extend(general_chunks)
        print(f"  Total chunks a indexar: {len(chunks)}")
        
        print("  Generando embeddings...")
        chunks = generate_embeddings(chunks, model)

        store_in_qdrant(chunks, force_recreate=first)
        first = False

    print("\n✅ Ingesta completada para todos los PDFs.")

if __name__ == "__main__":
    main()