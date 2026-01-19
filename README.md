# Microservicio de Autenticación y Onboarding Multi-tenant

Microservicio altamente reutilizable y configurable para autenticación y onboarding de empresas usando **FastAPI**, **PostgreSQL con RLS**, y **Google Cloud Identity Platform**.

## 🏗️ Arquitectura

- **Framework**: FastAPI (Python 3.12.x requerido)
- **Base de Datos**: PostgreSQL (Google Cloud SQL) con Row Level Security (RLS)
- **ORM**: SQLAlchemy 2.0 (Async) + Alembic
- **Autenticación**: Google Cloud Identity Platform (Firebase Admin SDK)
- **Multi-tenant**: Base de datos compartida con discriminador de columna y RLS

**⚠️ Requisito de Python**: Este proyecto requiere **Python 3.12.x** (no 3.13) debido a incompatibilidades con versiones específicas de `asyncpg` y `pydantic-core`.

## 📁 Estructura del Proyecto

```
firebase_auth/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicación FastAPI principal
│   ├── config.py               # Configuración con pydantic-settings
│   ├── database.py             # Session Manager con soporte RLS
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # TenantAwareModel (modelo base)
│   │   └── company.py          # Modelo Company
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── company.py          # Esquemas Pydantic para Company
│   │   └── onboarding.py       # Esquemas para onboarding
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth_middleware.py  # Middleware de autenticación Firebase
│   └── routers/
│       ├── __init__.py
│       ├── health.py           # Endpoint de health check
│       └── onboarding.py       # Endpoint de registro de empresas
├── alembic/                    # Migraciones de base de datos
├── scripts/
│   └── generate_rls_policies.py  # Generador de SQL para RLS
├── .env.example                # Plantilla de variables de entorno
├── requirements.txt            # Dependencias Python
├── alembic.ini                 # Configuración de Alembic
└── README.md                   # Este archivo
```

## 🚀 Instalación

### 1. Clonar y configurar entorno

Tienes dos opciones para instalar las dependencias:

#### Opción A: Usando `uv` (Recomendado - Más rápido)

```bash
# Crear entorno virtual con Python 3.12 (requerido)
uv venv --python 3.12.6

# Activar el entorno
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
uv pip install -r requirements.txt
```

**Nota importante**: Este proyecto requiere **Python 3.12** (no 3.13) debido a incompatibilidades con `asyncpg==0.29.0` y `pydantic-core==2.14.1`. El archivo `.python-version` está configurado para usar Python 3.12.6.

#### Opción B: Usando `pip` tradicional

```bash
# Crear entorno virtual
python3.12 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

**⚠️ Requisito de versión**: Asegúrate de usar **Python 3.12.x** (no 3.13). Puedes verificar tu versión con:
```bash
python --version
```

### 2. Configurar variables de entorno

Copia `.env.example` a `.env` y configura los valores:

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```env
PROJECT_NAME=mi_proyecto_auth
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=tu_password
DB_NAME=auth_db
FIREBASE_CREDENTIALS_PATH=./credentials/service-account-key.json
```

### 3. Configurar Firebase

Tienes dos opciones para las credenciales de Firebase:

#### Opción A: Google Cloud Secret Manager (Recomendado para Producción)

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto o selecciona uno existente
3. Habilita **Identity Platform API** y **Secret Manager API**
4. Crea una cuenta de servicio con permisos de **Secret Manager Secret Accessor**
5. Crea el JSON de credenciales de la cuenta de servicio
6. Crea un secreto en Secret Manager:
   ```bash
   # Subir el JSON como secreto
   gcloud secrets create firebase-service-account-key \
     --project=your-gcp-project-id \
     --data-file=./service-account-key.json
   ```
7. Configura las variables en `.env`:
   ```env
   USE_SECRET_MANAGER=true
   GCP_PROJECT_ID=your-gcp-project-id
   FIREBASE_CREDENTIALS_SECRET_NAME=firebase-service-account-key
   ```

**Nota**: La aplicación debe ejecutarse con permisos de Secret Manager. En GCP (Cloud Run, GKE, etc.), esto se configura mediante Service Accounts.

#### Opción B: Archivo JSON Local (Solo para Desarrollo)

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto o selecciona uno existente
3. Habilita **Identity Platform API**
4. Crea una cuenta de servicio y descarga el JSON de credenciales
5. Coloca el archivo JSON en `credentials/service-account-key.json`
6. Configura las variables en `.env`:
   ```env
   USE_SECRET_MANAGER=false
   FIREBASE_CREDENTIALS_PATH=./credentials/service-account-key.json
   ```

**⚠️ IMPORTANTE**: Nunca commitees archivos de credenciales. Usa Secret Manager en producción.

### 4. Configurar base de datos

```bash
# Asegúrate de tener el entorno virtual activado
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Crear base de datos PostgreSQL
createdb auth_db

# Ejecutar migraciones
alembic upgrade head
```

### 5. Activar Row Level Security (RLS)

**IMPORTANTE**: Debes ejecutar el script SQL como **superusuario** de PostgreSQL:

```bash
# Asegúrate de tener el entorno virtual activado
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Generar el SQL de políticas RLS
python scripts/generate_rls_policies.py

# Ejecutar el SQL generado (como superusuario)
psql -h localhost -U postgres -d auth_db -f scripts/rls_policies.sql
```

O manualmente desde `psql`:

```sql
-- Conectarse como superusuario
psql -h localhost -U postgres -d auth_db

-- Ejecutar el contenido de scripts/rls_policies.sql
```

## 🔧 Uso

### Iniciar el servidor

```bash
# Asegúrate de tener el entorno virtual activado
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Iniciar el servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El servicio estará disponible en: `http://localhost:8000`

### Documentación API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 Endpoints

### Health Check

```bash
GET /health
```

### Onboarding de Empresa

```bash
POST /onboarding/register-company
Content-Type: application/json

{
  "company_name": "Mi Empresa S.A.",
  "company_display_name": "Mi Empresa",
  "company_description": "Descripción de la empresa",
  "admin_user": {
    "email": "admin@miempresa.com",
    "password": "SecurePassword123!",
    "display_name": "Administrador"
  }
}
```

**Respuesta exitosa**:

```json
{
  "tenant_id": "abc123xyz",
  "company_id": "abc123xyz",
  "admin_user_id": "user123",
  "message": "Empresa y usuario administrador creados exitosamente"
}
```

## 🔐 Autenticación

Todas las rutas (excepto `/health` y `/public/*`) requieren autenticación mediante token Bearer:

```bash
Authorization: Bearer <firebase_id_token>
```

El middleware:
1. Verifica el token con Firebase Admin SDK
2. Extrae el `tenant_id` del claim `firebase.tenant`
3. Inyecta el `tenant_id` en el contexto de la request
4. El `SessionManager` establece `app.current_tenant` antes de cada consulta SQL

## 🏢 Multi-tenant y RLS

### Cómo funciona

1. **Session Manager**: Antes de cada consulta, ejecuta:
   ```sql
   SET LOCAL app.current_tenant = 'tenant_id_del_usuario';
   ```

2. **Políticas RLS**: PostgreSQL filtra automáticamente las filas según `app.current_tenant`

3. **Modelo Base**: `TenantAwareModel` incluye automáticamente la columna `tenant_id` en todas las tablas

### Agregar nuevas tablas con RLS

1. Hereda de `TenantAwareModel`:

```python
from app.models.base import TenantAwareModel

class MiModelo(TenantAwareModel):
    __tablename__ = "mi_tabla"
    # ... tus columnas
```

2. Ejecuta migración:

```bash
# Asegúrate de tener el entorno virtual activado
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

alembic revision --autogenerate -m "crear tabla mi_tabla"
alembic upgrade head
```

3. Crea políticas RLS (usa `scripts/generate_rls_policies.py` como plantilla)

## 🔄 Migraciones de Base de Datos

```bash
# Asegúrate de tener el entorno virtual activado
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Crear nueva migración
alembic revision --autogenerate -m "descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1
```

## 🧪 Testing

```bash
# Ejemplo de test con curl
curl -X POST http://localhost:8000/onboarding/register-company \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "admin_user": {
      "email": "admin@test.com",
      "password": "Test123456!"
    }
  }'
```

## 📝 Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `PROJECT_NAME` | Nombre del proyecto | ✅ |
| `DB_HOST` | Host de PostgreSQL | ✅ |
| `DB_USER` | Usuario de PostgreSQL | ✅ |
| `DB_PASSWORD` | Contraseña de PostgreSQL | ✅ |
| `DB_NAME` | Nombre de la base de datos | ✅ |
| `USE_SECRET_MANAGER` | Usar Secret Manager (true) o archivo (false) | ❌ (default: `true`) |
| `GCP_PROJECT_ID` | ID del proyecto de Google Cloud | ✅ (si `USE_SECRET_MANAGER=true`) |
| `FIREBASE_CREDENTIALS_SECRET_NAME` | Nombre del secreto en Secret Manager | ✅ (si `USE_SECRET_MANAGER=true`) |
| `FIREBASE_CREDENTIALS_PATH` | Ruta al JSON de credenciales | ✅ (si `USE_SECRET_MANAGER=false`) |
| `TENANT_ID_COLUMN_NAME` | Nombre de columna tenant (default: `tenant_id`) | ❌ |
| `RLS_SETTING_NAME` | Variable de sesión RLS (default: `app.current_tenant`) | ❌ |
| `ENVIRONMENT` | Entorno (development/production) | ❌ |
| `DEBUG` | Modo debug | ❌ |

## ⚙️ Requisitos del Sistema

- **Python**: 3.12.x (no 3.13) - Verifica con `python --version`
- **PostgreSQL**: 12+ (para soporte de RLS)
- **Google Cloud SDK**: Para usar Secret Manager (opcional)
- **uv** (opcional pero recomendado): Para instalación más rápida de dependencias

### Verificar versión de Python

```bash
python --version  # Debe mostrar Python 3.12.x
```

Si tienes Python 3.13 instalado, puedes usar `pyenv` o `uv` para instalar Python 3.12:

```bash
# Con pyenv
pyenv install 3.12.6
pyenv local 3.12.6

# Con uv
uv python install 3.12.6
uv python pin 3.12.6
```

## 🛡️ Seguridad

- ✅ Autenticación mediante Firebase Identity Platform
- ✅ Row Level Security (RLS) en PostgreSQL
- ✅ Validación de datos con Pydantic
- ✅ Manejo robusto de errores
- ✅ Transacciones atómicas en onboarding
- ⚠️ **NUNCA** commitees archivos de credenciales (`.gitignore` configurado)

## 🧪 Testing

### Ejecutar Tests

```bash
# Asegúrate de tener el entorno virtual activado
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Las dependencias de testing ya están incluidas en requirements.txt
# Si usas uv:
uv pip install -r requirements.txt
# O si usas pip tradicional:
pip install -r requirements.txt

# Ejecutar todos los tests
pytest

# Ejecutar tests con verbose
pytest -v

# Ejecutar tests con cobertura
pytest --cov=app --cov-report=html

# Ejecutar un test específico
pytest tests/test_config.py

# Ejecutar tests asíncronos
pytest tests/test_database.py -v
```

### Estructura de Tests

```
tests/
├── __init__.py
├── conftest.py              # Configuración compartida y fixtures
├── test_config.py           # Tests de configuración
├── test_database.py          # Tests de base de datos y Session Manager
├── test_models.py            # Tests de modelos
├── test_secret_manager.py    # Tests de Secret Manager
├── test_middleware.py        # Tests de middleware de autenticación
├── test_routers.py           # Tests de routers
├── test_dependencies.py      # Tests de dependencias
└── fixtures/                # Archivos de prueba
```

### Cobertura de Tests

Los tests cubren:
- ✅ Configuración y validación de settings
- ✅ Session Manager y RLS
- ✅ Modelos de base de datos
- ✅ Utilidades de Secret Manager
- ✅ Middleware de autenticación
- ✅ Routers (health, onboarding)
- ✅ Dependencias de FastAPI

## 📚 Recursos y Documentación

### Documentación del Proyecto

- [Configuración de RLS en PostgreSQL](./docs/RLS_SETUP.md)
- [Configuración de Secret Manager](./docs/SECRET_MANAGER_SETUP.md)

### Referencias Externas

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Google Cloud Identity Platform](https://cloud.google.com/identity-platform)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)

## 🤝 Contribución

Este microservicio está diseñado para ser **altamente reutilizable**. Para usarlo en otro proyecto:

1. Copia la estructura del proyecto
2. Asegúrate de usar Python 3.12.x
3. Crea un entorno virtual: `uv venv --python 3.12.6` o `python3.12 -m venv venv`
4. Instala las dependencias: `uv pip install -r requirements.txt` o `pip install -r requirements.txt`
5. Ajusta las variables de entorno
6. Personaliza los modelos según tus necesidades
7. Agrega tus propios endpoints

## 🔧 Troubleshooting

### Error: "asyncpg no se puede compilar con Python 3.13"

**Solución**: Usa Python 3.12.x. El proyecto está configurado para usar Python 3.12.6 mediante el archivo `.python-version`.

```bash
# Verificar versión actual
python --version

# Si tienes 3.13, instala 3.12.6
uv python install 3.12.6
uv venv --python 3.12.6
```

### Error: "pydantic-core falla al compilar"

**Solución**: Asegúrate de usar Python 3.12.x y las versiones exactas especificadas en `requirements.txt`.

### Error con `uv pip install`

**Solución**: Crea un entorno virtual explícito con la versión correcta de Python:

```bash
uv venv --python 3.12.6
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.
