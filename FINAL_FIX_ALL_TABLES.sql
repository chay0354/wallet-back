-- FINAL FIX: Create all tables and ensure they're exposed to the API
-- Run this ENTIRE script in Supabase SQL Editor

-- ============================================
-- 1. CREATE USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at DESC);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access" ON public.users;
CREATE POLICY "Service role full access" ON public.users FOR ALL USING (true);

-- ============================================
-- 2. CREATE WALLETS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.wallets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    balance DECIMAL(15, 2) NOT NULL DEFAULT 1000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON public.wallets(user_id);

ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access" ON public.wallets;
DROP POLICY IF EXISTS "Users can view own wallet" ON public.wallets;
DROP POLICY IF EXISTS "Users can update own wallet" ON public.wallets;

CREATE POLICY "Service role full access" ON public.wallets FOR ALL USING (true);
CREATE POLICY "Users can view own wallet" ON public.wallets FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own wallet" ON public.wallets FOR UPDATE USING (auth.uid() = user_id);

-- ============================================
-- 3. CREATE TRANSACTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    from_user_id UUID NOT NULL,
    to_user_id UUID NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON public.transactions(from_user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON public.transactions(to_user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON public.transactions(created_at DESC);

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access" ON public.transactions;
DROP POLICY IF EXISTS "Users can view own transactions" ON public.transactions;

CREATE POLICY "Service role full access" ON public.transactions FOR ALL USING (true);
CREATE POLICY "Users can view own transactions" ON public.transactions 
    FOR SELECT USING (auth.uid() = from_user_id OR auth.uid() = to_user_id);

-- ============================================
-- 4. AUTO-CREATE USER FUNCTION
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, full_name)
    VALUES (NEW.id, NEW.email, COALESCE(NEW.raw_user_meta_data->>'full_name', ''))
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- 5. MIGRATE EXISTING USERS
-- ============================================
INSERT INTO public.users (id, email, full_name, created_at)
SELECT id, email, COALESCE(raw_user_meta_data->>'full_name', ''), created_at
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.users WHERE id IS NOT NULL)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 6. VERIFY TABLES EXIST
-- ============================================
SELECT 
    'users' as table_name,
    COUNT(*) as row_count,
    'Table exists' as status
FROM public.users
UNION ALL
SELECT 
    'wallets' as table_name,
    COUNT(*) as row_count,
    'Table exists' as status
FROM public.wallets
UNION ALL
SELECT 
    'transactions' as table_name,
    COUNT(*) as row_count,
    'Table exists' as status
FROM public.transactions;


