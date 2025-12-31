# PowerShell script to create .env file
$envContent = @"
SUPABASE_URL=https://cerdtvnhqmebiayclxcd.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlcmR0dm5ocW1lYmlheWNseGNkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcxMjQ2ODIsImV4cCI6MjA4MjcwMDY4Mn0.-uXDP5Dy6w2Rn6ro7O6dfMHBTHKQGiboMC1MwC0H4vo
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlcmR0dm5ocW1lYmlheWNseGNkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzEyNDY4MiwiZXhwIjoyMDgyNzAwNjgyfQ.Q4ENANl5JhDb5Lu4KQwSD0oE313ZNRTJ4Ev0oQ8DhtQ
DATABASE_URL=postgres://postgres.cerdtvnhqmebiayclxcd:N5aZEvq03w6UZGJ9@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
"@

if (Test-Path ".env") {
    Write-Host ".env file already exists. Skipping creation." -ForegroundColor Yellow
} else {
    $envContent | Out-File -FilePath ".env" -Encoding utf8
    Write-Host ".env file created successfully!" -ForegroundColor Green
}


