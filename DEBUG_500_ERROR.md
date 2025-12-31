# Debugging 500 Internal Server Error

## Steps to Debug:

1. **Restart your backend server** to see the detailed error messages:
   ```powershell
   # Stop server (Ctrl+C)
   python main.py
   ```

2. **Check the console output** - You should now see detailed error messages like:
   ```
   Error in get_balance: [error message]
   Traceback: [full stack trace]
   ```

3. **Common Issues and Fixes:**

### Issue 1: Users table doesn't exist
**Error:** `Could not find the table 'public.users'`
**Fix:** Run the SQL script from `create_users_table_complete.sql` in Supabase

### Issue 2: Wallets table doesn't exist
**Error:** `Could not find the table 'public.wallets'`
**Fix:** Run the SQL script from `setup_database.sql` in Supabase

### Issue 3: Transactions table doesn't exist
**Error:** `Could not find the table 'public.transactions'`
**Fix:** Run the SQL script from `setup_database.sql` in Supabase

### Issue 4: RLS (Row Level Security) blocking access
**Error:** `new row violates row-level security policy`
**Fix:** Make sure the service role policy exists:
```sql
CREATE POLICY "Service role full access" ON public.users
    FOR ALL USING (true);
```

## Quick Fix - Run All SQL Scripts:

1. Go to Supabase SQL Editor
2. Run `setup_database.sql` (creates wallets and transactions tables)
3. Run `create_users_table_complete.sql` (creates users table)

## After Fixing:

Restart the backend server and the errors should be resolved.


