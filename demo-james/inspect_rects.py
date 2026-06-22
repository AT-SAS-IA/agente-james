import fitz

def main():
    doc = fitz.open("data/CATALOGO-JAMES-v_3.pdf")
    print("=== PAGE DIMENSIONS ===")
    for i, page in enumerate(doc):
        rect = page.rect
        print(f"Page {i+1}: Width={rect.width}, Height={rect.height} | Ratio={rect.width/rect.height:.2f}")
    doc.close()

if __name__ == "__main__":
    main()
