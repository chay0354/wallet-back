-- Create admin user in Supabase
-- Run this in Supabase SQL Editor to verify/administer the admin account

-- Note: You need to sign up the admin user first through the app with:
-- Email: admin@admin
-- Password: 123456

-- After signing up, run this to ensure admin is in users table:
INSERT INTO public.users (id, email, full_name, created_at)
SELECT 
    id,
    email,
    'Administrator' as full_name,
    created_at
FROM auth.users
WHERE email = 'admin@admin'
ON CONFLICT (id) DO UPDATE SET full_name = 'Administrator';

-- Verify admin user exists
SELECT 
    u.id,
    u.email,
    u.full_name,
    w.balance
FROM public.users u
LEFT JOIN public.wallets w ON u.id = w.user_id
WHERE u.email = 'admin@admin';

