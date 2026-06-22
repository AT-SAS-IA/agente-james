import json
from pathlib import Path

def main():
    json_path = Path("catalogo_james_productos.json")
    if not json_path.exists():
        print("JSON catalog not found.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)
        
    page_5_products = [p for p in products if p["source_page"] == 5]
    print(f"=== Page 5 Products ({len(page_5_products)}) ===")
    for p in page_5_products:
        print(f"Model: {p['model']} | Color: {p['color']} | Specs: {p['specs']} | Dims: {p['dimensions_mm']}")

if __name__ == "__main__":
    main()
