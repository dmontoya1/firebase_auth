
-- =====================================================
-- Script de Row Level Security (RLS) para Multi-tenant
-- =====================================================
-- Este script debe ejecutarse como superusuario en PostgreSQL
-- 
-- Configuración:
--   - Columna de tenant: tenant_id
--   - Variable de sesión: app.current_tenant
-- =====================================================

-- Habilitar la extensión para variables de sesión personalizadas (si es necesario)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- =====================================================
-- 1. Habilitar RLS en la tabla companies
-- =====================================================

ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- 2. Política para SELECT (lectura)
-- =====================================================
-- Los usuarios solo pueden ver registros de su tenant
-- Los superusuarios pueden ver todo

CREATE POLICY companies_select_policy ON companies
    FOR SELECT
    USING (
        -- Permitir si el usuario es superusuario
        current_setting('is_superuser', true) = 'on'
        OR
        -- Permitir si el tenant_id coincide con la variable de sesión
        tenant_id = current_setting('app.current_tenant', true)
    );

-- =====================================================
-- 3. Política para INSERT (inserción)
-- =====================================================
-- Los usuarios solo pueden insertar registros con su tenant_id
-- Los superusuarios pueden insertar cualquier registro

CREATE POLICY companies_insert_policy ON companies
    FOR INSERT
    WITH CHECK (
        -- Permitir si el usuario es superusuario
        current_setting('is_superuser', true) = 'on'
        OR
        -- Permitir si el tenant_id del nuevo registro coincide con la variable de sesión
        tenant_id = current_setting('app.current_tenant', true)
    );

-- =====================================================
-- 4. Política para UPDATE (actualización)
-- =====================================================
-- Los usuarios solo pueden actualizar registros de su tenant
-- Los superusuarios pueden actualizar cualquier registro

CREATE POLICY companies_update_policy ON companies
    FOR UPDATE
    USING (
        -- Permitir si el usuario es superusuario
        current_setting('is_superuser', true) = 'on'
        OR
        -- Permitir si el tenant_id coincide con la variable de sesión
        tenant_id = current_setting('app.current_tenant', true)
    )
    WITH CHECK (
        -- Permitir si el usuario es superusuario
        current_setting('is_superuser', true) = 'on'
        OR
        -- Permitir si el tenant_id del registro actualizado coincide con la variable de sesión
        tenant_id = current_setting('app.current_tenant', true)
    );

-- =====================================================
-- 5. Política para DELETE (eliminación)
-- =====================================================
-- Los usuarios solo pueden eliminar registros de su tenant
-- Los superusuarios pueden eliminar cualquier registro

CREATE POLICY companies_delete_policy ON companies
    FOR DELETE
    USING (
        -- Permitir si el usuario es superusuario
        current_setting('is_superuser', true) = 'on'
        OR
        -- Permitir si el tenant_id coincide con la variable de sesión
        tenant_id = current_setting('app.current_tenant', true)
    );

-- =====================================================
-- NOTAS IMPORTANTES:
-- =====================================================
-- 1. Las políticas anteriores asumen que la variable de sesión
--    'app.current_tenant' se establece ANTES de cada consulta.
--    Esto se hace automáticamente en el SessionManager de la aplicación.
--
-- 2. Para otras tablas que hereden de TenantAwareModel, deberás
--    crear políticas similares. Puedes usar este script como plantilla.
--
-- 3. Para verificar que RLS está funcionando:
--    - Conecta como usuario de aplicación (no superusuario)
--    - Ejecuta: SET LOCAL app.current_tenant = 'test-tenant-id';
--    - Intenta SELECT * FROM companies;
--    - Solo deberías ver registros con tenant_id = 'test-tenant-id'
--
-- 4. Para deshabilitar RLS temporalmente (solo para debugging):
--    ALTER TABLE companies DISABLE ROW LEVEL SECURITY;
--
-- 5. Para eliminar todas las políticas:
--    DROP POLICY IF EXISTS companies_select_policy ON companies;
--    DROP POLICY IF EXISTS companies_delete_policy ON companies;
--    DROP POLICY IF EXISTS companies_update_policy ON companies;
--    DROP POLICY IF EXISTS companies_insert_policy ON companies;
-- =====================================================
