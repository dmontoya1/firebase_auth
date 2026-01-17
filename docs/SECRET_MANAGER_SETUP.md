# Configuración de Google Cloud Secret Manager

Esta guía explica cómo configurar Google Cloud Secret Manager para almacenar las credenciales de Firebase de forma segura.

## 🎯 ¿Por qué usar Secret Manager?

- **Seguridad**: Las credenciales nunca se almacenan en el código o archivos del repositorio
- **Rotación**: Fácil rotación de credenciales sin cambiar código
- **Auditoría**: Registro de acceso a secretos
- **Mejores prácticas**: Estándar de la industria para gestión de secretos

## 📋 Prerrequisitos

- Proyecto de Google Cloud creado
- `gcloud` CLI instalado y configurado
- Permisos de administrador o editor en el proyecto

## 🚀 Configuración Paso a Paso

### 1. Habilitar APIs Necesarias

```bash
# Habilitar Secret Manager API
gcloud services enable secretmanager.googleapis.com --project=your-gcp-project-id

# Habilitar Identity Platform API (si aún no está habilitada)
gcloud services enable identitytoolkit.googleapis.com --project=your-gcp-project-id
```

### 2. Crear Cuenta de Servicio para Firebase

1. Ve a [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Haz clic en "Create Service Account"
3. Nombre: `firebase-admin-service`
4. Descripción: "Service account para Firebase Admin SDK"
5. Haz clic en "Create and Continue"
6. Asigna el rol: **Firebase Admin SDK Administrator Service Agent**
7. Haz clic en "Done"

### 3. Crear y Descargar Clave JSON

1. En la lista de cuentas de servicio, haz clic en la que acabas de crear
2. Ve a la pestaña "Keys"
3. Haz clic en "Add Key" > "Create new key"
4. Selecciona "JSON" y haz clic en "Create"
5. El archivo se descargará automáticamente

### 4. Crear Secreto en Secret Manager

```bash
# Crear el secreto con el archivo JSON descargado
gcloud secrets create firebase-service-account-key \
  --project=your-gcp-project-id \
  --data-file=./path/to/downloaded-service-account-key.json \
  --replication-policy="automatic"
```

**Nota**: Reemplaza:
- `your-gcp-project-id` con tu ID de proyecto
- `firebase-service-account-key` con el nombre que quieras para el secreto
- `./path/to/downloaded-service-account-key.json` con la ruta al archivo descargado

### 5. Configurar Permisos del Secreto

La cuenta de servicio que ejecuta la aplicación necesita permisos para leer el secreto:

```bash
# Obtener el email de la cuenta de servicio que ejecuta la app
# (En Cloud Run, GKE, etc., esto es la cuenta de servicio del servicio)

# Otorgar permiso de lectura
gcloud secrets add-iam-policy-binding firebase-service-account-key \
  --project=your-gcp-project-id \
  --member="serviceAccount:your-app-service-account@your-project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Para desarrollo local**, puedes usar tu cuenta de usuario:

```bash
# Otorgar permiso a tu cuenta de usuario
gcloud secrets add-iam-policy-binding firebase-service-account-key \
  --project=your-gcp-project-id \
  --member="user:your-email@gmail.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 6. Configurar Variables de Entorno

Edita tu archivo `.env`:

```env
USE_SECRET_MANAGER=true
GCP_PROJECT_ID=your-gcp-project-id
FIREBASE_CREDENTIALS_SECRET_NAME=firebase-service-account-key
```

### 7. Autenticación para Desarrollo Local

Para desarrollo local, necesitas autenticarte con `gcloud`:

```bash
# Autenticarse con Google Cloud
gcloud auth application-default login

# O usar una cuenta de servicio
export GOOGLE_APPLICATION_CREDENTIALS="./path/to/service-account-key.json"
```

**Nota**: En producción (Cloud Run, GKE, Compute Engine), la autenticación se maneja automáticamente mediante la cuenta de servicio asignada al servicio.

## 🔄 Rotación de Credenciales

Si necesitas rotar las credenciales:

1. **Crear nueva versión del secreto**:

```bash
gcloud secrets versions add firebase-service-account-key \
  --project=your-gcp-project-id \
  --data-file=./new-service-account-key.json
```

2. **La aplicación usará automáticamente la versión "latest"**

3. **Si necesitas deshabilitar una versión antigua**:

```bash
gcloud secrets versions disable VERSION_NUMBER \
  --secret=firebase-service-account-key \
  --project=your-gcp-project-id
```

## 🧪 Verificación

### Verificar que el secreto existe

```bash
gcloud secrets describe firebase-service-account-key \
  --project=your-gcp-project-id
```

### Verificar permisos

```bash
gcloud secrets get-iam-policy firebase-service-account-key \
  --project=your-gcp-project-id
```

### Probar acceso desde Python

```python
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
name = f"projects/your-gcp-project-id/secrets/firebase-service-account-key/versions/latest"
response = client.access_secret_version(request={"name": name})
print(response.payload.data.decode("UTF-8"))
```

## 🏗️ Configuración para Diferentes Entornos

### Cloud Run

1. Asigna una cuenta de servicio al servicio de Cloud Run
2. Asegúrate de que tenga el rol `roles/secretmanager.secretAccessor`
3. Las variables de entorno se configuran en Cloud Run:
   ```bash
   gcloud run services update your-service \
     --set-env-vars="USE_SECRET_MANAGER=true,GCP_PROJECT_ID=your-project-id,FIREBASE_CREDENTIALS_SECRET_NAME=firebase-service-account-key"
   ```

### Google Kubernetes Engine (GKE)

1. Crea un Secret de Kubernetes que apunte a Secret Manager usando [Secret Store CSI Driver](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity) o
2. Usa Workload Identity para que los pods accedan directamente a Secret Manager

### Compute Engine

1. Asigna una cuenta de servicio a la VM
2. Asegúrate de que tenga el rol `roles/secretmanager.secretAccessor`
3. Configura las variables de entorno en el sistema o en el servicio

## 🔒 Mejores Prácticas

1. **Nunca commitees credenciales**: Usa Secret Manager siempre en producción
2. **Principio de menor privilegio**: Solo otorga permisos necesarios
3. **Rotación regular**: Rota las credenciales periódicamente
4. **Auditoría**: Revisa los logs de acceso a secretos
5. **Versionado**: Usa versiones específicas en producción si necesitas control fino

## 📚 Referencias

- [Google Cloud Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
