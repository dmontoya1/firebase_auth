# Configuración de Row Level Security (RLS) en PostgreSQL

Este documento explica cómo activar Row Level Security (RLS) en PostgreSQL para el sistema multi-tenant.

## 📋 Prerrequisitos

- Acceso como **superusuario** a la base de datos PostgreSQL
- Base de datos creada y migraciones aplicadas
- Conocimiento básico de SQL

## 🚀 Pasos para Activar RLS

### Opción 1: Usando el Script Generado (Recomendado)

1. **Generar el SQL de políticas RLS**:

```bash
python scripts/generate_rls_policies.py
```

Esto creará el archivo `scripts/rls_policies.sql` con todas las políticas necesarias.

2. **Ejecutar el SQL como superusuario**:

```bash
psql -h localhost -U postgres -d auth_db -f scripts/rls_policies.sql
```

O desde `psql`:

```bash
psql -h localhost -U postgres -d auth_db
\i scripts/rls_policies.sql
```

### Opción 2: Manualmente desde psql

1. **Conectarse como superusuario**:

```bash
psql -h localhost -U postgres -d auth_db
```

2. **Habilitar RLS en la tabla**:

```sql
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
```

3. **Crear políticas** (ejemplo para SELECT):

```sql
CREATE POLICY companies_select_policy ON companies
    FOR SELECT
    USING (
        current_setting('is_superuser', true) = 'on'
        OR
        tenant_id = current_setting('app.current_tenant', true)
    );
```

4. **Repetir para INSERT, UPDATE y DELETE** (ver `scripts/rls_policies.sql` para el SQL completo).

## ✅ Verificación

### 1. Verificar que RLS está habilitado

```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND tablename = 'companies';
```

Debería mostrar `rowsecurity = true`.

### 2. Verificar políticas creadas

```sql
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'companies';
```

Deberías ver 4 políticas: SELECT, INSERT, UPDATE, DELETE.

### 3. Probar RLS (como usuario de aplicación)

```sql
-- Conectarse como usuario de aplicación (no superusuario)
psql -h localhost -U app_user -d auth_db

-- Establecer el tenant
SET LOCAL app.current_tenant = 'test-tenant-id';

-- Intentar ver todas las empresas
SELECT * FROM companies;

-- Solo deberías ver empresas con tenant_id = 'test-tenant-id'
```

### 4. Probar que superusuario ve todo

```sql
-- Conectarse como superusuario
psql -h localhost -U postgres -d auth_db

-- Ver todas las empresas (sin establecer tenant)
SELECT * FROM companies;

-- Deberías ver TODAS las empresas, independientemente del tenant
```

## 🔧 Configuración de la Variable de Sesión

La aplicación establece automáticamente `app.current_tenant` antes de cada consulta mediante el `SessionManager`. Sin embargo, para debugging puedes establecerla manualmente:

```sql
-- Para la sesión actual
SET LOCAL app.current_tenant = 'tu-tenant-id';

-- Para todas las consultas en esta conexión
SET app.current_tenant = 'tu-tenant-id';

-- Ver el valor actual
SHOW app.current_tenant;
```

## 🆕 Agregar RLS a Nuevas Tablas

Cuando crees una nueva tabla que herede de `TenantAwareModel`:

1. **Habilitar RLS**:

```sql
ALTER TABLE mi_tabla ENABLE ROW LEVEL SECURITY;
```

2. **Crear políticas** (usa `scripts/generate_rls_policies.py` como plantilla):

```sql
CREATE POLICY mi_tabla_select_policy ON mi_tabla
    FOR SELECT
    USING (
        current_setting('is_superuser', true) = 'on'
        OR
        tenant_id = current_setting('app.current_tenant', true)
    );

-- Repetir para INSERT, UPDATE, DELETE
```

## ⚠️ Troubleshooting

### Problema: "No puedo ver ningún registro"

**Causa**: La variable `app.current_tenant` no está establecida.

**Solución**: Verifica que el middleware de autenticación esté extrayendo correctamente el `tenant_id` del token y que el `SessionManager` lo esté estableciendo.

### Problema: "Error: setting 'app.current_tenant' does not exist"

**Causa**: PostgreSQL no reconoce la variable personalizada.

**Solución**: Esto es normal. PostgreSQL permite establecer variables personalizadas sin declararlas previamente. Si el error persiste, verifica que estés usando `SET LOCAL` o `SET` correctamente.

### Problema: "Las políticas no se están aplicando"

**Causa**: Posiblemente RLS no está habilitado o las políticas tienen errores.

**Solución**:
1. Verifica que RLS esté habilitado: `SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'companies';`
2. Verifica las políticas: `SELECT * FROM pg_policies WHERE tablename = 'companies';`
3. Revisa los logs de PostgreSQL para errores en las políticas.

## 📚 Referencias

- [PostgreSQL Row Level Security Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [PostgreSQL Custom Variables](https://www.postgresql.org/docs/current/runtime-config-custom.html)
