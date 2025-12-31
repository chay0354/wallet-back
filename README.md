# Digital Wallet Backend

## Setup Instructions

### 1. Install Dependencies

On Windows, use one of these methods:

**Option 1 (Recommended):**
```powershell
python -m pip install -r requirements.txt
```

**Option 2:**
```powershell
py -m pip install -r requirements.txt
```

**Option 3:** If you have Python Launcher:
```powershell
python3 -m pip install -r requirements.txt
```

### 2. Environment Variables

Make sure you have a `.env` file in this directory with:
```
SUPABASE_URL=https://cerdtvnhqmebiayclxcd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

The `.env` file should already be created with the correct values.

### 3. Run the Server

```powershell
python main.py
```

Or:
```powershell
python -m uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## Troubleshooting

### "pip is not recognized"
- Use `python -m pip` instead of just `pip`
- Make sure Python is installed and in your PATH
- Try `py -m pip` if `python` doesn't work

### "supabase_url is required"
- Make sure the `.env` file exists in the `wallet-back` directory
- Check that the file is named exactly `.env` (not `.env.txt` or similar)
- Verify the SUPABASE_URL value is correct

### Database Setup
Don't forget to run the SQL script from `setup_database.sql` in your Supabase dashboard!


