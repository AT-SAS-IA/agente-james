#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor estructurado para CATALOGO-JAMES-v_3.pdf

Objetivo:
- Extraer productos directamente del PDF.
- Evitar inventar campos.
- Mantener raw_text, page y source para auditoría.
- Generar JSON y CSV.

Uso:
  pip install pymupdf pandas openpyxl
  python extract_catalog_james.py data/CATALOGO-JAMES-v_3.pdf

Salidas:
  catalogo_james_productos.json
  catalogo_james_productos.csv
  catalogo_james_productos.xlsx

Notas:
- El parser es determinístico: no usa LLM.
- Si un campo no está explícito en el texto del bloque, queda en null.
- Se conserva raw_text por producto para validar contra el PDF.
"""

import re
import json
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("Falta PyMuPDF. Instalá con: pip install pymupdf")

try:
    import pandas as pd
except ImportError:
    pd = None


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\ufb01", "fi")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_decimal(value: str) -> Optional[float]:
    if value is None:
        return None
    value = value.strip().replace(".", "").replace(",", ".")
    try:
        n = float(value)
        return int(n) if n.is_integer() else n
    except Exception:
        return None


def first_number(pattern: str, text: str, flags=re.I) -> Optional[float]:
    m = re.search(pattern, text, flags)
    if not m:
        return None
    return normalize_decimal(m.group(1))


def extract_dimensions(text: str) -> Optional[Dict[str, Optional[float]]]:
    # ancho x profundidad x altura 550 x 550 x 1590 mm
    patterns = [
        r"(?:Dimensiones[^:]*:\s*)?(?:ancho\s*x\s*profundidad\s*x\s*altura\s*)?(\d{2,4})\s*x\s*(\d{2,4})\s*x\s*(\d{2,4})\s*mm",
        r"(?:Dimensiones[^:]*:\s*)?(\d{2,4})\s*x\s*(\d{2,4})\s*x\s*(\d{2,4})\s*mm",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return {"width": int(m.group(1)), "depth": int(m.group(2)), "height": int(m.group(3))}
    # diameter x height cases are not standard dimensions_mm; still keep as width/depth equal diameter
    m = re.search(r"di[aá]metro\s*x\s*altura\s*(\d{2,4})\s*x\s*(\d{2,4})\s*mm", text, re.I)
    if m:
        d = int(m.group(1)); h = int(m.group(2))
        return {"width": d, "depth": d, "height": h}
    return None


def extract_installation_dimensions(text: str) -> Optional[Dict[str, Optional[float]]]:
    m = re.search(r"instalaci[oó]n[^:]*:\s*ancho\s*x\s*profundidad(?:\s*x\s*altura)?\s*(\d{2,4})\s*x\s*(\d{2,4})(?:\s*x\s*(\d{2,4}))?\s*mm", text, re.I)
    if m:
        return {"width": int(m.group(1)), "depth": int(m.group(2)), "height": int(m.group(3)) if m.group(3) else None}
    return None


def extract_energy(text: str) -> Optional[str]:
    m = re.search(r"Eficiencia energ[eé]tica\s*:?\s*([A-G])\b", text, re.I)
    return m.group(1).upper() if m else None


def extract_color(text_before_specs: str) -> Optional[str]:
    t = text_before_specs
    patterns = [
        r"COLOR\s+([A-ZÁÉÍÓÚÜÑ /-]+)",
        r"FRENTE\s+DE\s+([A-ZÁÉÍÓÚÜÑ /-]+)",
        r"FRENTE\s+([A-ZÁÉÍÓÚÜÑ /-]+)",
        r"\b(ACERO INOXIDABLE|INOXIDABLE|DARK INOXIDABLE|DARK INOX|S[IÍ]MIL ACERO INOXIDABLE|VIDRIO NEGRO|NEGRO|BLANCO|GRIS|ROJO|VERDE|SILVER|NOGAL OSCURO|NOGAL CLARO|NEGRO MATE)\b",
    ]
    for pat in patterns:
        m = re.search(pat, t, re.I)
        if m:
            color = m.group(1).strip(" _-*.")
            color = re.sub(r"\s+", " ", color)
            return color.title().replace("Inox", "INOX").replace("Inoxidable", "Inoxidable")
    return None


def page_category(page_text: str) -> Dict[str, Optional[str]]:
    t = page_text.upper()
    category = None
    sub = None
    # order matters
    if "TELEVISORES" in t:
        category = "Televisores"; sub = "LED Smart TV"
    elif "ACONDICIONADORES DE AIRE" in t:
        category = "Acondicionadores de Aire Split"
    elif "DESHUMIDIFICADORES" in t:
        category = "Deshumidificadores"
    elif "REFRIGERADORES" in t or "REFRIGERADOR" in t:
        category = "Refrigeradores"
        if "FRÍO HÚMEDO" in t or "FRIO HUMEDO" in t: sub = "Frío Húmedo"
        if "FRÍO SECO CON DISPENSADOR" in t or "FRIO SECO CON DISPENSADOR" in t: sub = "Frío Seco con Dispensador"
        elif "FRÍO SECO" in t or "FRIO SECO" in t: sub = "Frío Seco"
        if "COMBI" in t: sub = "Combi"
        if "FRENCH DOOR" in t: sub = "French Door"
        if "MULTIDOOR" in t: sub = "Multidoor"
        if "SIDE" in t and "SIDE" in t: sub = "Side by Side"
    elif "LÍNEA PANELABLES" in t or "LINEA PANELABLES" in t or "EMPOTRABLES" in t and "RJC" in t:
        category = "Refrigeradores"; sub = "Panelables / Empotrables"
    elif "FREEZERS" in t:
        category = "Freezers"
    elif "VITRINAS" in t:
        category = "Vitrinas"; sub = "Refrigerador Vitrina"
    elif "LAVASECARROPAS" in t:
        category = "Lavasecarropas"
    elif "LAVARROPAS" in t:
        category = "Lavarropas"
        if "CARGA FRONTAL" in t: sub = "Carga Frontal"
        elif "CARGA SUPERIOR" in t: sub = "Carga Superior"
    elif "SECARROPAS" in t:
        category = "Secarropas"
    elif "CENTRIFUGADORA" in t:
        category = "Centrifugadora"
    elif "LAVAVAJILLAS" in t:
        category = "Lavavajillas"
    elif "COCINAS" in t or "COCINA" in t:
        category = "Cocinas"
        if "ELÉCTRICAS" in t or "ELECTRICAS" in t: sub = "Eléctricas"
        elif "COMBINADA 3+1 DOBLE HORNO" in t: sub = "Combinada 3+1 Doble Horno"
        elif "COMBINADAS 3+1" in t: sub = "Combinadas 3+1"
        elif "COMBINADAS" in t: sub = "Combinadas"
        elif "GRILL" in t: sub = "Gas con Grill"
        elif "VIDRIO NEGRO" in t: sub = "Gas con Mesada de Vidrio Negro"
        else: sub = "A Gas"
    elif "ANAFES" in t:
        category = "Anafes"
        if "INDUCCIÓN" in t or "INDUCCION" in t: sub = "Inducción Magnética"
        elif "VITROCER" in t: sub = "Vitrocerámica"
        elif "GAS" in t: sub = "Empotrar a Gas"
    elif "HORNOS DE EMPOTRAR" in t:
        category = "Hornos de Empotrar"
    elif "CAMPANAS" in t:
        category = "Campanas Extractoras"
    elif "PURIFICADORES" in t:
        category = "Purificadores"
    elif "EXTRACTORES DE AIRE" in t:
        category = "Extractores de Aire para Baño"
    elif "HORNOS ELÉCTRICOS" in t or "HORNOS ELECTRICOS" in t:
        category = "Hornos Eléctricos"; sub = "De Mesa"
    elif "MICROONDAS" in t:
        category = "Hornos Microondas"
    elif "ASPIRADORAS" in t:
        category = "Aspiradoras"
    elif "PEQUEÑOS ELECTRODOMÉSTICOS" in t or "PEQUENOS ELECTRODOMESTICOS" in t:
        category = "Pequeños Electrodomésticos"
    elif "ESTUFA A SUPERGÁS" in t or "ESTUFA A SUPERGAS" in t:
        category = "Estufas"; sub = "A Supergás"
    elif "ESTUFAS ELÉCTRICAS" in t or "ESTUFAS ELECTRICAS" in t:
        category = "Estufas"; sub = "Eléctricas"
    elif "VENTILADORES DE TECHO" in t:
        category = "Ventiladores"; sub = "De Techo"
    elif "VENTILADORES" in t:
        category = "Ventiladores"
    elif "TERMOTANQUES" in t:
        category = "Termotanques Eléctricos"
    return {"category": category, "subcategory": sub}


def split_model_declarations(block: str) -> List[Dict[str, Any]]:
    """Detects one or more model declarations at start of a block.
    Example: Modelo RJ 25 MB COLOR BLANCO Modelo RJ 25 M INOX ACERO INOXIDABLE · shared specs
    Returns model/color candidates and shared text.
    """
    # Find all Modelo tokens inside block before first bullet/spec delimiter
    # Keep delimiters so shared specs are reused for variants.
    starts = list(re.finditer(r"\b(?:Modelo|MODELO)\s+", block, re.I))
    if not starts:
        return []
    items = []
    # A model declaration extends until next Modelo or a bullet separator
    for i, st in enumerate(starts):
        start = st.start()
        end = starts[i+1].start() if i+1 < len(starts) else len(block)
        decl_plus = block[start:end].strip()
        # If last declaration, split declaration from specs at first bullet
        parts = re.split(r"\s+[·•]\s+", decl_plus, maxsplit=1)
        decl = parts[0]
        shared = parts[1] if len(parts) > 1 else ""
        # Clean model name: text after Modelo up to known color/feature markers
        name = re.sub(r"^\b(?:Modelo|MODELO)\s+", "", decl, flags=re.I).strip()
        name = re.split(r"\b(COLOR|FRENTE|ACERO|DARK|S[IÍ]MIL|VIDRIO|INOXIDABLE|FR[IÍ]O|DE EMPOTRAR|PORT[ÁA]TIL)\b", name, maxsplit=1, flags=re.I)[0].strip(" _-*.")
        name = re.sub(r"\s+", " ", name)
        if not name or len(name) < 2:
            continue
        items.append({"model": name, "decl": decl, "tail": shared})
    # determine common specs = text after the last declaration's first bullet, or all after last decl
    last_decl_start = starts[-1].start()
    common_text = block[last_decl_start:]
    common_parts = re.split(r"\s+[·•]\s+", common_text, maxsplit=1)
    common_specs = common_parts[1] if len(common_parts) > 1 else ""
    # If an item lacks tail, give it common specs too.
    for it in items:
        it["shared_specs"] = common_specs
    return items


def extract_specs(text: str) -> Dict[str, Any]:
    specs: Dict[str, Any] = {}
    patterns = [
        ("capacidad_bruta_L", r"Capacidad bruta(?: total)?\s*:?\s*([\d,.]+)\s*L"),
        ("capacidad_util_total_L", r"Capacidad útil total\s*:?\s*([\d,.]+)\s*L"),
        ("capacidad_util_L", r"Capacidad útil\s*:?\s*([\d,.]+)\s*L"),
        ("refrigerador_L", r"Refrigerador\s*([\d,.]+)\s*L"),
        ("freezer_L", r"Freezer\s*([\d,.]+)\s*L"),
        ("congelador_L", r"Congelador\s*([\d,.]+)\s*L"),
        ("capacidad_kg", r"Capacidad(?: de lavado)?\s*:?\s*([\d,.]+)\s*kg"),
        ("capacidad_secado_kg", r"Capacidad de secado\s*:?\s*([\d,.]+)\s*kg"),
        ("programas", r"([\d,.]+)\s*programas"),
        ("potencia_W", r"Potencia(?: total)?\s*:?\s*([\d,.]+)\s*W"),
        ("rpm", r"([\d,.]+)\s*RPM"),
        ("cubiertos", r"Capacidad\s*:?\s*([\d,.]+)\s*cubiertos"),
        ("diametro_plato_mm", r"Di[aá]metro (?:del )?plato\s*:?\s*([\d,.]+)\s*mm"),
        ("extraccion_m3h", r"(?:Potencia|Caudal m[aá]ximo) de extracci[oó]n\s*:?\s*([\d,.]+)\s*m³?/h"),
        ("ruido_dB", r"Nivel de ruido\s*:?\s*([\d,.]+)\s*dB"),
        ("peso_kg", r"Peso\s*:?\s*([\d,.]+)\s*kg"),
    ]
    for key, pat in patterns:
        val = first_number(pat, text)
        if val is not None:
            specs[key] = val
    return specs


def extract_features(text: str) -> List[str]:
    # split bullet-like feature clauses, excluding fields already parsed
    raw = re.split(r"\s+[·•]\s+", text)
    features = []
    skip_prefixes = ("Capacidad", "Dimensiones", "Eficiencia", "Potencia", "Peso", "Diámetro", "Diametro")
    for part in raw:
        p = part.strip(" .;:_-*\n\t")
        if not p or len(p) < 3:
            continue
        if p.startswith(skip_prefixes):
            continue
        if len(p) > 160:
            p = p[:157].rstrip() + "..."
        # Avoid repeated model declarations as features
        if re.match(r"^(Modelo|MODELO)\b", p):
            continue
        features.append(p)
    # unique preserving order
    seen=set(); out=[]
    for f in features:
        k=f.lower()
        if k not in seen:
            seen.add(k); out.append(f)
    return out[:20]


def parse_products_from_text(pages: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    products = []
    current_category = None
    current_subcategory = None
    for page in pages:
        pno = page["page"]
        text = page["text"]
        cat = page_category(text)
        if cat.get("category"):
            current_category = cat["category"]
            current_subcategory = cat.get("subcategory")
            
        if not current_category:
            continue
            
        # Normalize model keyword separation
        t = re.sub(r"(?<!\s)(Modelo|MODELO)\s+", r" \1 ", text)
        blocks = re.split(r"(?=\b(?:Modelo|MODELO)\s+)", t, flags=re.I)
        for block in blocks:
            if not re.match(r"\b(?:Modelo|MODELO)\s+", block.strip(), re.I):
                continue
            block = clean_text(block)
            declarations = split_model_declarations(block)
            if not declarations:
                continue
            # Shared specs are the full block after first bullet; use for all variants if needed.
            full_specs = re.split(r"\s+[·•]\s+", block, maxsplit=1)
            full_after_bullet = full_specs[1] if len(full_specs) > 1 else block
            for decl in declarations:
                raw = decl.get("shared_specs") or full_after_bullet
                combined = decl["decl"] + " · " + raw
                dims = extract_dimensions(combined)
                product = {
                    "category": current_category,
                    "subcategory": current_subcategory,
                    "model": decl["model"],
                    "color": extract_color(decl["decl"]),
                    "specs": extract_specs(combined),
                    "features": extract_features(combined),
                    "dimensions_mm": dims,
                    "installation_dimensions_mm": extract_installation_dimensions(combined),
                    "energy_rating": extract_energy(combined),
                    "source_page": pno,
                    "source": source,
                    "raw_text": combined.strip()
                }
                # subtype fix by product/page-local info
                upper = combined.upper()
                if product["category"] == "Freezers":
                    if product["model"].startswith("FHJ"):
                        product["subcategory"] = "Horizontal"
                    elif product["model"].startswith("FVJ"):
                        product["subcategory"] = "Vertical"
                if product["category"] == "Cocinas" and "C-60 SPRO" in product["model"]:
                    product["subcategory"] = "Combinada Semiprofesional"
                if product["category"] == "Hornos Eléctricos" and "HEE" in product["model"]:
                    product["category"] = "Hornos de Empotrar"
                    product["subcategory"] = None
                products.append(product)
    # Deduplicate by page+model+color keeping first
    dedup=[]; seen=set()
    for p in products:
        key=(p["source_page"], p["model"].lower(), (p.get("color") or "").lower())
        if key not in seen:
            seen.add(key); dedup.append(p)
    return dedup


def extract_page_zones_layout_aware(page, physical_page_num: int) -> List[Dict[str, Any]]:
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
            zones.append({"page": left_page_num, "text": left_text})
        if right_text:
            zones.append({"page": right_page_num, "text": right_text})
    else:
        page_num = physical_page_num if physical_page_num == 1 else (2 * physical_page_num - 4)
        if left_text:
            zones.append({"page": page_num, "text": left_text})

    return zones


def extract_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc, start=1):
        zones = extract_page_zones_layout_aware(page, i)
        pages.extend(zones)
    doc.close()
    return pages


def flatten_for_csv(product: Dict[str, Any]) -> Dict[str, Any]:
    d = {
        "category": product.get("category"),
        "subcategory": product.get("subcategory"),
        "model": product.get("model"),
        "color": product.get("color"),
        "energy_rating": product.get("energy_rating"),
        "source_page": product.get("source_page"),
        "source": product.get("source"),
        "features": " | ".join(product.get("features") or []),
        "raw_text": product.get("raw_text"),
    }
    dims = product.get("dimensions_mm") or {}
    d.update({"width_mm": dims.get("width"), "depth_mm": dims.get("depth"), "height_mm": dims.get("height")})
    inst = product.get("installation_dimensions_mm") or {}
    d.update({"install_width_mm": inst.get("width"), "install_depth_mm": inst.get("depth"), "install_height_mm": inst.get("height")})
    for k, v in (product.get("specs") or {}).items():
        d[f"spec_{k}"] = v
    return d


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python extract_catalog_james.py data/CATALOGO-JAMES-v_3.pdf")
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        raise SystemExit(f"No existe el PDF: {pdf_path}")
    pages = extract_pages(pdf_path)
    products = parse_products_from_text(pages, source=pdf_path.name)

    out_json = Path("catalogo_james_productos.json")
    out_csv = Path("catalogo_james_productos.csv")
    out_xlsx = Path("catalogo_james_productos.xlsx")

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    rows = [flatten_for_csv(p) for p in products]
    # Make CSV with union of keys
    keys=[]
    for row in rows:
        for k in row.keys():
            if k not in keys:
                keys.append(k)
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

    has_xlsx = False
    if pd:
        try:
            import openpyxl
            pd.DataFrame(rows).to_excel(out_xlsx, index=False, engine="openpyxl")
            has_xlsx = True
        except ImportError:
            print("Nota: No se exportó a XLSX porque 'openpyxl' no está instalado.")

    print(f"Productos extraídos: {len(products)}")
    print(f"JSON: {out_json.resolve()}")
    print(f"CSV:  {out_csv.resolve()}")
    if has_xlsx:
        print(f"XLSX: {out_xlsx.resolve()}")

    # Summary by category
    counts = {}
    for p in products:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    print("\nResumen por categoría:")
    for k, v in sorted(counts.items(), key=lambda x: x[0]):
        print(f"- {k}: {v}")

if __name__ == "__main__":
    main()
