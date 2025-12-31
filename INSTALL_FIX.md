# Installation Fix for Rust/DNS Issues

If you're getting Rust compilation errors when installing dependencies, try these solutions:

## Solution 1: Install without version pins (Recommended)

This will use the latest versions with pre-built wheels:

```powershell
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn[standard] python-dotenv supabase python-jose[cryptography] passlib[bcrypt] python-multipart pydantic httpx
```

## Solution 2: Install pydantic separately first

Sometimes installing pydantic separately helps:

```powershell
python -m pip install --upgrade pip
python -m pip install pydantic --only-binary :all:
python -m pip install -r requirements.txt
```

## Solution 3: Use pre-built wheels only

Force pip to only use pre-built wheels (no compilation):

```powershell
python -m pip install --upgrade pip
python -m pip install --only-binary :all: -r requirements.txt
```

If that fails, install packages one by one:

```powershell
python -m pip install --only-binary :all: fastapi
python -m pip install --only-binary :all: uvicorn[standard]
python -m pip install --only-binary :all: python-dotenv
python -m pip install --only-binary :all: supabase
python -m pip install --only-binary :all: python-jose[cryptography]
python -m pip install --only-binary :all: passlib[bcrypt]
python -m pip install --only-binary :all: python-multipart
python -m pip install --only-binary :all: pydantic
python -m pip install --only-binary :all: httpx
```

## Solution 4: Use Python 3.11 or 3.12

Python 3.14 might be too new and not have pre-built wheels. Consider using Python 3.11 or 3.12 which have better package support.

## Solution 5: Install Rust manually (if needed)

If you really need to compile, install Rust first:
1. Download from https://rustup.rs/
2. Install Rust
3. Then try installing packages again


