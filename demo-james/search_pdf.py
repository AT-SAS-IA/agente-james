import fitz
import os

def search_text():
    pdf_path = "data/CATALOGO-JAMES-v_3.pdf"
    if not os.path.exists(pdf_path):
        print(f"PDF not found at {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    # 1. Search for RJ 225
    print("\n--- Searching for 'RJ 225' ---")
    for i, page in enumerate(doc):
        text = page.get_text()
        if "RJ 225" in text or "225" in text:
            print(f"Match on Page {i+1}:")
            lines = text.splitlines()
            for line in lines:
                if "225" in line or "RJ" in line:
                    print(f"  → {line.strip()}")
                    
    # 2. Search for 194 L
    print("\n--- Searching for '194' ---")
    for i, page in enumerate(doc):
        text = page.get_text()
        if "194" in text:
            print(f"Match on Page {i+1}:")
            lines = text.splitlines()
            for line in lines:
                if "194" in line or "L" in line:
                    print(f"  → {line.strip()}")

    doc.close()

if __name__ == "__main__":
    search_text()
