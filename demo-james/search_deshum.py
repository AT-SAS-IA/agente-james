import fitz

def main():
    doc = fitz.open("data/CATALOGO-JAMES-v_3.pdf")
    matches = []
    for i, page in enumerate(doc):
        text = page.get_text().lower()
        if "deshumidificador" in text:
            matches.append((i+1, page.get_text()[:200].strip()))
    print("Matches:", matches)
    doc.close()

if __name__ == "__main__":
    main()
