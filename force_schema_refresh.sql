-- Force Schema Refresh - Grant explicit permissions
-- Run this after creating tables to ensure API can access them

-- Grant permissions to all roles
GRANT ALL ON public.users TO postgres, anon, authenticated, service_role;
GRANT ALL ON public.wallets TO postgres, anon, authenticated, service_role;
GRANT ALL ON public.transactions TO postgres, anon, authenticated, service_role;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;

-- Verify tables are accessible
SELECT 
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('users', 'wallets', 'transactions')
ORDER BY table_name;


