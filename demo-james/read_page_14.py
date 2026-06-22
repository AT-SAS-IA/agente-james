import fitz

def main():
    doc = fitz.open("data/CATALOGO-JAMES-v_3.pdf")
    print("=== PAGE 14 ===")
    print(doc[13].get_text()) # Page 14 is index 13
    doc.close()

if __name__ == "__main__":
    main()
