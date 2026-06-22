# Guía de Despliegue en Azure Container Apps (ACA)

Esta guía explica cómo subir el contenedor unificado de la PoC de JAMES a Azure Container Apps. Como la base de datos vectorial de Qdrant ahora funciona in-process (SQLite) y se autocompila dentro de la imagen de Docker, no se necesitan múltiples contenedores ni almacenamiento externo persistente.

---

## Prerrequisitos

1. **Azure CLI** instalado y habiendo iniciado sesión (`az login`).
2. **Docker** instalado y corriendo en tu máquina.
3. Un grupo de recursos de Azure existente o creado para la PoC.

---

## Paso 1: Asegurar que el catálogo esté indexado en el host
Antes de compilar la imagen para Azure, asegúrate de que el catálogo esté extraído e indexado localmente. Esto genera la carpeta `./qdrant_db` con los datos vectoriales reales que se copiarán en el build:

```bash
# 1. Extraer catálogo en JSON
py scripts/extract_catalog_james.py data/CATALOGO-JAMES-v_3.pdf

# 2. Correr la ingesta (apaga la API antes si da error de lock)
docker compose down
docker compose build
docker compose run --rm api python ingest.py
```

---

## Paso 2: Crear un Azure Container Registry (ACR)
Si no tenés un registro de contenedores en Azure, creá uno (debe tener un nombre único global en minúsculas y sin caracteres especiales):

```bash
# Crear el registro (ejemplo de nombre: registroJamesPoc)
az acr create \
  --resource-group <mi-grupo-recursos> \
  --name <nombre-registro> \
  --sku Basic \
  --admin-enabled true
```

---

## Paso 3: Autenticarse y subir la imagen
1. **Iniciar sesión en el ACR:**
   ```bash
   az acr login --name <nombre-registro>
   ```

2. **Buildeas la imagen local:**
   ```bash
   docker build -t james-api:latest .
   ```

3. **Taggear la imagen para el ACR:**
   ```bash
   docker tag james-api:latest <nombre-registro>.azurecr.io/james-api:latest
   ```

4. **Subir la imagen al registro:**
   ```bash
   docker push <nombre-registro>.azurecr.io/james-api:latest
   ```

---

## Paso 4: Crear la Azure Container App (ACA)
Desplegá la aplicación especificando el puerto `8000` (puerto del servidor Uvicorn) y pasando las credenciales de Azure OpenAI como variables de entorno:

```bash
az containerapp create \
  --name james-rag-app \
  --resource-group <mi-grupo-recursos> \
  --image <nombre-registro>.azurecr.io/james-api:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    ENDPOINT="https://pmont-me9y33fz-eastus2.cognitiveservices.azure.com/" \
    DEPLOYMENT="SovacaGTP5" \
    SUBSCRIPTION_KEY="<tu-subscription-key-de-openai>" \
    API_VERSION="2024-12-01-preview"
```

---

## Consideraciones del Despliegue
* **In-process DB:** Como el `/app/qdrant_db` está pre-baked en la imagen, el contenedor levantará de inmediato con los 288 chunks vectorizados listos.
* **Escalado:** ACA puede escalar a 0 si la aplicación no recibe tráfico (ahorrando costos) o escalar horizontalmente. Dado que las consultas son de lectura, múltiples réplicas pueden leer el SQLite de Qdrant concurrentemente sin problemas de bloqueos.
* **Frontend:** Podrás acceder a la aplicación desde la URL pública HTTPS que te devuelva el comando `az containerapp create`.
