# ⚙️ Windows Setup Guide - Email Triage Environment

Your system doesn't have Python properly installed. Here are your options:

## Option 1: Quick Fix - Disable Microsoft Store Python Alias (Fastest)

This allows the real Python installation (if present) to be found:

1. **Open Settings** → Search for "Manage app execution aliases"
2. **Scroll down** to find:
   - `python.exe`
   - `python3.exe`
3. **Toggle OFF** (disable both)
4. **Close Settings**
5. **Restart PowerShell/CMD**
6. Try again:
   ```powershell
   python --version
   pip install -r requirements.txt
   ```

If Python is still not found after this, proceed to Option 2.

---

## Option 2: Install Python from python.org (Recommended)

1. **Download** Python 3.10+ from https://www.python.org/downloads/
   - Click "Download Python 3.11" (or 3.12)
   
2. **Run installer**
   - ✅ **CHECK**: "Add Python to PATH" (IMPORTANT!)
   - ✅ **CHECK**: "Install pip"
   - Click "Install Now"

3. **Verify installation** (restart PowerShell first):
   ```powershell
   python --version
   pip --version
   ```

4. **Install dependencies**:
   ```powershell
   cd c:\Users\AYUSH\Desktop\zscaler\email-triage-env
   pip install -r requirements.txt
   ```

5. **Test environment**:
   ```powershell
   python scripts/test_environment.py
   ```

---

## Option 3: Use Python via Microsoft Store (If Already Installed)

1. **Open Microsoft Store** (if you installed Python from there)
2. Search for "Python 3.11" or "Python 3.12"
3. **Click "Install"** if not already installed
4. **Wait for installation** to complete
5. Then try:
   ```powershell
   python --version
   pip install -r requirements.txt
   ```

---

## Option 4: Docker Alternative (No Python Needed Locally)

If you don't want to install Python, use Docker instead:

1. **Install Docker Desktop** from https://www.docker.com/products/docker-desktop
2. **Start Docker Desktop** (important - must be running)
3. **Build image**:
   ```powershell
   docker build -t email-triage-env .
   ```
4. **Run tests**:
   ```powershell
   docker run email-triage-env python scripts/test_environment.py
   ```
5. **Run baseline** (with API key):
   ```powershell
   docker run -e OPENAI_API_KEY="sk-..." email-triage-env python -m scripts.baseline_inference
   ```

---

## Recommended Path for You

**Step 1**: Try Option 1 (disable Microsoft Store alias) - takes < 1 minute
**Step 2**: If that doesn't work, use Option 2 (install real Python) - takes ~5 minutes
**Step 3**: If you want to avoid Python locally, use Option 4 (Docker) - takes ~10 minutes

---

## Verify Your System

After attempting setup, check:

```powershell
# Should show version number
python --version

# Should show Python's pip version
pip --version

# Should say "✓ Imports OK"
python -c "print('✓ Python works!')"
```

---

## If You're Still Stuck

Try running this diagnostic:

```powershell
# Where is Python?
Get-Command python

# Is pip available?
Get-Command pip

# Check all Python-related apps
Get-ChildItem "$env:USERPROFILE\AppData\Local\Programs\Python*" -ErrorAction SilentlyContinue
```

Then try one more time:
```powershell
cd c:\Users\AYUSH\Desktop\zscaler\email-triage-env
pip install --upgrade pip
pip install -r requirements.txt
python scripts/test_environment.py
```

---

## Once Setup is Complete

Then you can run:

```powershell
# Test environment (no API key needed)
python scripts/test_environment.py

# Run baseline (with API key)
$env:OPENAI_API_KEY = "sk-..."
python -m scripts.baseline_inference

# Try examples
python -c "from email_triage.environment import EmailTriageEnv; print('✓ Environment loaded')"
```

---

**Let me know which option you'd like to try, or if you need help with any of these steps!**
