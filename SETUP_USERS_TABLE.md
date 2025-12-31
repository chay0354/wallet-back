# URGENT: Create Users Table

## Error You're Seeing:
```
Error getting user by ID: {'code': 'PGRST205', 'message': "Could not find the table 'public.users' in the schema cache"}
```

## Quick Fix:

1. **Go to Supabase Dashboard:**
   - Visit: https://supabase.com/dashboard/project/cerdtvnhqmebiayclxcd
   - Or: https://cerdtvnhqmebiayclxcd.supabase.co

2. **Open SQL Editor:**
   - Click on "SQL Editor" in the left sidebar
   - Click "New query"

3. **Copy and Paste this SQL:**
   ```sql
   -- Create users table
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

   -- Enable RLS
   ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

   -- Service role policy (allows backend to access)
   CREATE POLICY "Service role full access" ON public.users
       FOR ALL USING (true);

   -- Auto-create user function
   CREATE OR REPLACE FUNCTION public.handle_new_user()
   RETURNS TRIGGER AS $$
   BEGIN
       INSERT INTO public.users (id, email, full_name)
       VALUES (
           NEW.id,
           NEW.email,
           COALESCE(NEW.raw_user_meta_data->>'full_name', '')
       )
       ON CONFLICT (id) DO NOTHING;
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql SECURITY DEFINER;

   -- Trigger to auto-create users
   DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
   CREATE TRIGGER on_auth_user_created
       AFTER INSERT ON auth.users
       FOR EACH ROW
       EXECUTE FUNCTION public.handle_new_user();

   -- Migrate existing users
   INSERT INTO public.users (id, email, full_name, created_at)
   SELECT 
       id,
       email,
       COALESCE(raw_user_meta_data->>'full_name', '') as full_name,
       created_at
   FROM auth.users
   WHERE id NOT IN (SELECT id FROM public.users)
   ON CONFLICT (id) DO NOTHING;
   ```

4. **Click "Run" or press Ctrl+Enter**

5. **Restart your backend server:**
   ```powershell
   # Stop the server (Ctrl+C)
   # Then restart:
   python main.py
   ```

## What This Does:

- Creates the `public.users` table
- Sets up indexes for fast lookups
- Creates a trigger to auto-create user profiles when someone signs up
- Migrates any existing users from `auth.users` to `public.users`
- Allows the backend to access the table

## After Running:

The error should be gone and your wallet should work properly!


