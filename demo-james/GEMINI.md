import os

# Definir el contenido del archivo Markdown
md_content = """# 🤖 Demo RAG – Agente de Consulta de Documentación (COPAC)

## 📌 Descripción
Esta demo implementa un agente conversacional basado en **RAG (Retrieval-Augmented Generation)**, diseñado para consultar documentación oficial en PDF (Términos y Condiciones, Beneficios, Reglamentos) mediante lenguaje natural.

El agente responde exclusivamente en base al contenido de los documentos indexados, citando fuente y página.

---

## 🎯 Objetivo
* Validar arquitectura RAG de bajo costo.
* Permitir consultas sobre múltiples PDFs.
* Garantizar respuestas verificables (con fuentes).
* Evitar generación de información inventada (alucinaciones).

---

## ⚙️ Funcionamiento

### 1. Ingesta de documentos
**PDF → Texto → Chunks → Embeddings → Qdrant**

* **Extracción de texto:** Uso de PyMuPDF.
* **Limpieza básica:** Sin perder semántica.
* **Chunking:** Fragmentos de ~800 caracteres con overlap.
* **Generación de embeddings:** Modelo local.
* **Indexación:** Almacenamiento en Qdrant junto a metadata básica.

### 2. Proceso de consulta
**Pregunta → Embedding → Búsqueda → Contexto → LLM → Respuesta**

* Se genera el embedding de la pregunta del usuario.
* Se buscan los chunks más similares en la base vectorial Qdrant.
* Se construye un prompt enriquecido con el contexto relevante.
* El LLM genera la respuesta final basada estrictamente en ese contexto.

---

## 📊 Interpretación de resultados

### 🔹 Score
El `score` representa la similitud semántica entre la pregunta y el fragmento recuperado:

| Score | Interpretación |
| :--- | :--- |
| **> 0.40** | Muy relevante |
| **0.30 – 0.40** | Relevante |
| **0.20 – 0.30** | Moderado |
| **< 0.20** | Bajo |

### 🔹 Múltiples resultados de la misma página
* El sistema trabaja con **fragmentos (chunks)**, no páginas completas.
* Una misma página puede generar varios chunks.
* Cada chunk tiene su propio score independiente.
* *Este es un comportamiento esperado y óptimo para la precisión.*

---

## ✅ Comportamiento esperado del agente
* ✅ Responde únicamente con información de los documentos.
* ✅ Cita siempre el nombre del documento y el número de página.
* ✅ Interpreta lenguaje natural (formal e informal).
* ✅ Rechaza preguntas fuera de dominio.
* ✅ Indica claramente cuando no posee información.

---

## ❌ Restricciones
El agente **NO**:
* ❌ Inventa información (tasas, montos, condiciones).
* ❌ Responde fuera del dominio de los documentos cargados.
* ❌ Infiere datos que no estén explícitos.

> **En caso de no encontrar información:**
> "No cuento con información sobre este tema en la documentación disponible."

---

## 🧪 Ejemplos de uso

### Preguntas válidas
* *"¿Qué servicios puedo realizar online?"*
* *"¿Qué pasa si pierdo mi contraseña?"*
* *"¿Dónde puedo ejercer mis derechos sobre mis datos?"*

### Preguntas inválidas
* *"¿Cuál es la tasa de interés?"*
* *"¿Cuánto dinero me pueden prestar?"*
* *"¿Cómo está el dólar hoy?"*

---

## 🏗️ Stack tecnológico (Demo)
* **Backend:** FastAPI
* **Base vectorial:** Qdrant (Docker)
* **Embeddings:** `sentence-transformers`
* **LLM:** Gemini (modelos gratuitos)
* **Extracción PDF:** PyMuPDF

---

## 🚀 Alcance de la demo
* 1 a 3 documentos PDF de prueba.
* Ingesta manual de archivos.
* Metadata básica (fuente, página).
* Sin autenticación de usuarios.
* Sin logging persistente de conversaciones.

---

## 🔄 Diferencia con producto final
La demo es una versión simplificada. Para una versión de producción se integrará:

1.  **Metadata estructurada:** Producto, vigencia, tipo de documento.
2.  **Ingesta incremental:** Control de versiones y cambios en documentos.
3.  **Enterprise Stack:** Embeddings y LLM vía Azure OpenAI.
4.  **Filtros avanzados:** Búsqueda por vigencia o categorías de producto.
5.  **Observabilidad:** Logging, monitoreo y feedback de usuario.
6.  **Frontend:** Interfaz de usuario profesional.

---

## 📌 Notas finales
* La precisión depende directamente de la calidad del contenido de los PDFs.
* El sistema responde en base al contexto recuperado dinámicamente.
* Este asistente es una herramienta de apoyo y **no reemplaza** los canales oficiales de atención.
"""

# Guardar el archivo
file_path = "Demo_RAG_COPAC.md"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"Archivo generado: {file_path}")