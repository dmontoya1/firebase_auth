# Postman - Firebase Auth API

Colección para probar el flujo completo del microservicio: **registrar compañía → login con el usuario de esa compañía → llamar a un endpoint protegido**.

## Importar en Postman

1. **Colección:** File → Import → `firebase_auth_api.postman_collection.json`
2. **Entorno:** File → Import → `firebase_auth_local.postman_environment.json`
3. Selecciona el entorno **"Firebase Auth - Local"** en el selector (arriba a la derecha).

## Configurar Firebase API Key

El login con Firebase (Identity Platform) requiere la **Web API Key** del proyecto:

1. Ve a [Firebase Console](https://console.firebase.google.com/) → tu proyecto (ej. metis-vertex-dev).
2. Project settings (engranaje) → **General**.
3. En "Your apps" o "Web API Key", copia la **API key**.
4. En Postman, en el entorno "Firebase Auth - Local", edita la variable **`firebase_api_key`** y pega esa clave.

## Orden de ejecución (prueba completa)

1. **Health** (opcional) – comprobar que el servidor responde.
2. **Register Company** – crea tenant, empresa y usuario admin.  
   - Se guardan automáticamente `tenant_id`, `admin_email` y `admin_password` en el entorno.
3. **Login Firebase** – obtiene un token con el usuario de la compañía.  
   - Se guarda automáticamente `id_token` en el entorno.
4. **My Company** – endpoint protegido con Bearer; usa `id_token` y devuelve la empresa del tenant.

Puedes usar **Collection Runner** y ejecutar la colección en ese orden para hacer la prueba de extremo a extremo.

## Variables del entorno

| Variable           | Descripción |
|-------------------|-------------|
| `base_url`        | URL del API (por defecto `http://localhost:8000`) |
| `firebase_api_key`| Web API Key de Firebase (obligatoria para Login Firebase) |
| `tenant_id`       | Se rellena tras "Register Company" |
| `id_token`        | Se rellena tras "Login Firebase" |
| `admin_email`     | Email del admin (por defecto el del body de Register Company) |
| `admin_password`  | Contraseña del admin (por defecto la del body de Register Company) |

## Requisitos

- Servidor local corriendo: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Base de datos con migraciones y RLS aplicado.
- Credenciales de Firebase (service account) configuradas para el proyecto (Identity Platform en el mismo proyecto).
