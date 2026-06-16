import re

def main():
    path = "app.py"
    try:
        # Read as bytes to avoid decoding crash
        with open(path, "rb") as f:
            content = f.read()
        
        # Decode as utf-8, ignoring invalid bytes
        decoded = content.decode("utf-8", errors="ignore")
        
        # Replace the problematic divider sections
        # We find any corrupt lines near {context} and {question}
        # and replace them with standard ASCII dividers.
        
        # Let's search for the end of SYSTEM_PROMPT
        # We can look for the key parts:
        pattern = r"CLAVE \(TE LO RESUMO A LO IMPORTANTE\).*?{question}\"\"\""
        
        replacement = """CLAVE (TE LO RESUMO A LO IMPORTANTE)

* menos listado
* más guía
* nunca cambiar categoría
* usar contexto siempre

===========================================
CONTEXTO DEL CATÁLOGO:
{context}

===========================================
PREGUNTA DEL USUARIO (CONSIDERAR HISTORIAL SI CORRESPONDE):
{question}\"\"\""""
        
        # If we can't do regex easily, let's do a simple string replacement
        # Let's clean up all occurrences of the double-line unicode dividers 
        # (and any corrupted characters resulting from them)
        
        cleaned = decoded
        # Let's clean out any non-ascii characters in the dividers
        # and replace them with standard dashes.
        lines = cleaned.splitlines()
        new_lines = []
        for line in lines:
            if "CONTEXTO DEL CATÁLOGO" in line:
                new_lines.append("===========================================")
                new_lines.append("CONTEXTO DEL CATÁLOGO:")
            elif "PREGUNTA DEL USUARIO" in line:
                new_lines.append("===========================================")
                new_lines.append("PREGUNTA DEL USUARIO (CONSIDERAR HISTORIAL SI CORRESPONDE):")
            elif "{question}\"\"\"" in line:
                new_lines.append("{question}\"\"\"")
            elif "CONTEXTO DEL CATÁLOGO" not in line and "PREGUNTA DEL USUARIO" not in line and "{question}" not in line and any(ord(c) > 1000 for c in line) and "🧊" not in line and "👉" not in line and "✅" not in line and "❌" not in line and "🌟" not in line and "📺" not in line and "🔥" not in line and "🌀" not in line and "🌬️" not in line and "📍" not in line and "🛠️" not in line:
                # This is likely a corrupted unicode divider line, skip it or replace with ascii
                if "{" not in line and "}" not in line:
                    continue
                new_lines.append(line)
            else:
                new_lines.append(line)
                
        cleaned = "\n".join(new_lines)
        
        # Write it back as clean UTF-8
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)
            
        print("Successfully repaired app.py encoding issues!")
        
    except Exception as e:
        print(f"Error repairing app.py: {e}")

if __name__ == "__main__":
    main()
