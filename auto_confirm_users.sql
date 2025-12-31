-- Auto-confirm all existing users (removes email confirmation requirement)
-- Run this in your Supabase SQL Editor

-- Update all users to have email_confirmed_at set to now
UPDATE auth.users 
SET email_confirmed_at = NOW() 
WHERE email_confirmed_at IS NULL;

-- Verify the update
SELECT 
    id, 
    email, 
    email_confirmed_at,
    created_at
FROM auth.users
ORDER BY created_at DESC;


