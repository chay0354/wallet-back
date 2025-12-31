# Users Table SQL Command

## Quick Copy-Paste SQL

Run this in your Supabase SQL Editor:

```sql
-- Create users table in public schema
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Service role full access" ON public.users
    FOR ALL USING (true);

-- Auto-create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
```

## What This Does

1. **Creates a `users` table** in the `public` schema that:
   - Links to `auth.users` via `id` (UUID)
   - Stores `email` and optional `full_name`
   - Has `created_at` and `updated_at` timestamps

2. **Creates indexes** for faster queries on email and created_at

3. **Sets up Row Level Security (RLS)** so users can only see/edit their own profile

4. **Auto-creates user profiles** - When a user signs up in `auth.users`, a corresponding record is automatically created in `public.users`

## Table Structure

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key, references `auth.users(id)` |
| `email` | TEXT | User's email (unique) |
| `full_name` | TEXT | User's full name (optional) |
| `created_at` | TIMESTAMP | When the profile was created |
| `updated_at` | TIMESTAMP | When the profile was last updated |

## Usage

After running this SQL:
- New signups will automatically get a profile in `public.users`
- You can query user profiles: `SELECT * FROM public.users WHERE email = 'user@example.com'`
- The table works alongside your existing `wallets` and `transactions` tables


