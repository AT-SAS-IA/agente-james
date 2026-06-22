# 🤖 Reglas del Agente (Workspace: Agente JAMES)

Este archivo define las reglas de comportamiento, la arquitectura y las pautas técnicas que deben seguir todos los agentes de IA (como Codex/Antigravity) que colaboren en este repositorio.

---

## 📌 Contexto del Proyecto
Este proyecto es una **Demo / PoC RAG (Retrieval-Augmented Generation)** para consultar el catálogo oficial de electrodomésticos de **JAMES**.
* **Dominio:** Asesoramiento comercial sobre heladeras, freezers, lavavajillas, microondas, secarropas, y otros productos de JAMES Uruguay.
* **Base de Datos:** Qdrant funcionando en modo **in-process (SQLite)** ubicado en `./demo-james/qdrant_db`. No hay servidores de base de datos externos.
* **Modelos:** Embeddings locales (`paraphrase-multilingual-MiniLM-L12-v2`) y chat completion mediante **Azure OpenAI** (`gpt-5-chat`/`gpt-4o` según el despliegue).

---

## 🛠️ Arquitectura y Stack Tecnológico
Cualquier desarrollo, modificación o refactorización debe respetar estas pautas:
1. **Frontend Unificado:** El frontend está escrito en HTML/JS vainilla dentro de `./demo-james/static/` y es servido directamente por FastAPI (`app.py`) en la raíz `/` mediante `FileResponse("static/index.html")`. No agregar servidores web estáticos separados.
2. **Rate Limiting Middleware:** Mantener siempre el middleware de limitación en `/chat` (máximo 30 peticiones/minuto por cliente IP). Debe detectar la IP real del cliente usando la cabecera `X-Forwarded-For` para ser compatible con proxies de Azure.
3. **Anti-Jailbreak (Seguridad):** El endpoint `/chat` debe validar preventivamente en Python las cadenas de inyección de prompt antes de llamar al LLM (palabras clave como `"ignora las instrucciones"`, `"system prompt"`, `"modo desarrollador"`, etc.) y rechazar la consulta inmediatamente.

---

## 💾 Reglas de Ingesta y Base de Datos (Qdrant)
* **Nombre de la Colección:** La colección por defecto en Qdrant es `"james-demo"`. El fallback en el código de `app.py` e `ingest.py` siempre debe ser `"james-demo"`.
* **Bloqueos de Base de Datos:** Como Qdrant corre in-process (SQLite), no se puede ejecutar `ingest.py` en el host mientras el contenedor de la API de FastAPI esté corriendo (retornará error de *lock*). El flujo seguro para re-indexar es:
  1. Detener el contenedor (`docker compose down`).
  2. Correr la ingesta localmente o en un contenedor temporal.
  3. Levantar la API nuevamente.

---

## 📋 Reglas de Estilo y Comportamiento del Agente
* **Preservación:** No modificar comentarios, imports o estructuras de `app.py` que no estén directamente relacionados con la tarea solicitada.
* **Modelos Reales:** Al dar respuestas del catálogo de JAMES, nunca alucinar modelos inexistentes (ej: no inventar `LVJ 8` o `FR 120`). Solo responder con modelos que aparezcan en los chunks recuperados del contexto (ej: `JN 50K`, `LV 10VN`, etc.) y siempre citar la página del catálogo correspondiente.
* **CORS:** Si se modifica CORS en `app.py`, mantenerlo permisivo únicamente para desarrollo local. En producción, el tráfico se sirve desde el mismo origen.
