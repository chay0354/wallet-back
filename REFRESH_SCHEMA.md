# Fix Schema Cache Issue - Tables Exist But API Can't See Them

## The Problem:
Your tables exist (users, wallets, transactions) but Supabase's PostgREST API can't see them because the schema cache hasn't refreshed.

## Solutions (Try in Order):

### Solution 1: Wait 2-3 Minutes
The cache usually refreshes automatically. Just wait 2-3 minutes after creating tables, then restart your backend.

### Solution 2: Restart Supabase Project
1. Go to Supabase Dashboard
2. Click on your project settings
3. Look for "Restart" or "Pause/Resume" option
4. Restart the project (this forces a schema cache refresh)

### Solution 3: Force Schema Reload via API Settings
1. Go to Supabase Dashboard
2. Navigate to **Settings** → **API**
3. Look for any "Reload Schema" or "Refresh" button
4. If available, click it

### Solution 4: Check API Settings
1. Go to **Settings** → **API** in Supabase Dashboard
2. Make sure "Expose tables via API" is enabled
3. Check that the tables are listed in the "Exposed tables" section

### Solution 5: Verify Tables Are in Public Schema
Run this SQL to confirm:
```sql
SELECT schemaname, tablename 
FROM pg_tables 
WHERE tablename IN ('users', 'wallets', 'transactions')
AND schemaname = 'public';
```

All should show `schemaname = 'public'`

### Solution 6: Grant Permissions Explicitly
Sometimes you need to grant explicit permissions:
```sql
GRANT ALL ON public.users TO postgres, anon, authenticated, service_role;
GRANT ALL ON public.wallets TO postgres, anon, authenticated, service_role;
GRANT ALL ON public.transactions TO postgres, anon, authenticated, service_role;
```

## After Trying Solutions:

1. **Wait 2-3 minutes** after running any SQL
2. **Restart your backend server**
3. **Test the API again**

The schema cache should refresh automatically, but it can take a few minutes.


