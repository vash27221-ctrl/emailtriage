# Testing & Deployment Guide

## Local Testing (Without OpenAI API)

You can test the environment locally without an API key:

### Test Suite

```bash
# Run all tests
python scripts/test_environment.py
```

This validates:
- ✓ All imports work
- ✓ Environment can initialize all tasks
- ✓ Episodes run without errors
- ✓ Graders produce valid scores
- ✓ OpenEnv spec compliance

### Manual Local Testing (Python)

```python
from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

# Initialize environment
env = EmailTriageEnv(task_id="task_1_easy")

# Run an episode
observation = env.reset()

done = False
while not done:
    # Random classification
    action = Action(
        action_type=ActionType.CLASSIFY,
        category=EmailCategory.URGENT,
        reason="Test"
    )
    
    observation, reward, done, info = env.step(action)
    print(f"Reward: {reward.step_reward}, Accuracy: {reward.accuracy:.2%}")

# Get final results
state = env.state()
grade = env.task.grade()

print(f"\nFinal Grade: {grade:.2f}/1.0")
print(f"Accuracy: {state.cumulative_reward:.2%}")
```

### Quick Validation

```bash
# Check imports
python -c "from email_triage.environment import EmailTriageEnv; print('✓ Imports OK')"

# Check task generation
python -c "from email_triage.environment import EmailTriageEnv; e = EmailTriageEnv(); print('✓ Environment OK')"

# Validate OpenEnv spec
python -c "from email_triage.openenv_spec import validate_environment_spec; validate_environment_spec()"
```

---

## Baseline Inference with OpenAI API

### 1. Get API Key

```bash
# Sign up at https://platform.openai.com
# Create API key in account settings
# Copy key
```

### 2. Set Environment Variable

**Linux/macOS**:
```bash
export OPENAI_API_KEY="sk-..."
```

**Windows (PowerShell)**:
```powershell
$env:OPENAI_API_KEY="sk-..."
```

**Windows (CMD)**:
```cmd
set OPENAI_API_KEY=sk-...
```

### 3. Run Baseline

```bash
python -m scripts.baseline_inference
```

### 4. Review Results

Results saved to `baseline_results.json`:

```json
{
  "task_1_easy": {
    "task_id": "task_1_easy",
    "difficulty": "easy",
    "total_emails": 10,
    "correct": 9,
    "wrong": 1,
    "accuracy": 0.9,
    "final_grade": 1.0,
    "results": [
      {
        "step": 1,
        "email_id": "email_1",
        "predicted": "spam",
        "ground_truth": "spam",
        "correct": true,
        "reward": 1.0
      }
    ]
  }
}
```

---

## Docker Testing

### Build Locally

```bash
docker build -t email-triage-env:latest .
```

### Run Tests in Container

```bash
# With test suite
docker run email-triage-env:latest python scripts/test_environment.py

# With baseline (requires API key)
docker run -e OPENAI_API_KEY="sk-..." email-triage-env:latest python -m scripts.baseline_inference
```

### Verify Image

```bash
# Check layers
docker history email-triage-env:latest

# Inspect
docker inspect email-triage-env:latest | grep -A 5 "Env"
```

---

## HuggingFace Spaces Deployment

### Step 1: Create Space

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Fill form:
   - **Owner**: Your username
   - **Space name**: `email-triage-env`
   - **License**: MIT
   - **Space SDK**: Docker
4. Create space

### Step 2: Clone & Push Code

```bash
# Clone the space repository
git clone https://huggingface.co/spaces/YOUR_USERNAME/email-triage-env
cd email-triage-env

# Remove any existing files (except .git)
rm -rf * .gitignore

# Copy all files from this repo
cp -r ../email-triage-env-local/* .

# Stage and commit
git add .
git commit -m "Initial email triage environment"

# Push to HF
git push
```

### Step 3: Configure Secrets

In HF Space settings:
1. Go to **Settings** → **Repository secrets**
2. Add secret:
   - **Name**: `OPENAI_API_KEY`
   - **Value**: Your API key
   - **Check**: "Private repo secret"
3. Save

### Step 4: Monitor Build

1. Go to **Logs** tab
2. Watch Docker build progress
3. Build typically takes 5-10 minutes
4. Once complete, space is live

### Step 5: View Results

- **Space URL**: `https://huggingface.co/spaces/YOUR_USERNAME/email-triage-env`
- **Logs**: Shows baseline results and any errors
- **Files**: View all in **Repository** tab

### Step 6: Update Space

To push code updates:

```bash
# Make changes to local code
# ... edit files ...

# Commit and push
git add .
git commit -m "Update scoring logic"
git push

# HF auto-rebuilds space
```

---

## Reproducibility Verification

### Deterministic Checks

Verify the environment is deterministic:

```python
from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

# Run 1
env1 = EmailTriageEnv("task_1_easy")
obs1 = env1.reset()
email_id_1 = obs1.current_email.id

# Run 2
env2 = EmailTriageEnv("task_1_easy")
obs2 = env2.reset()
email_id_2 = obs2.current_email.id

# Should be same email in same order (if not random-seeded)
print(f"Same sequence: {email_id_1 == email_id_2}")
```

### Reproducible Baseline

Same environment state should always produce same results:

```bash
# Run baseline twice
python -m scripts.baseline_inference > run1.log
python -m scripts.baseline_inference > run2.log

# Compare (should be identical)
diff run1.log run2.log
```

---

## Common Issues & Fixes

### Issue: `ImportError: No module named email_triage`

**Solution**: Install package in development mode:
```bash
cd email-triage-env
pip install -e .
```

### Issue: `OPENAI_API_KEY not found`

**Solution**: Set environment variable before running:
```bash
export OPENAI_API_KEY="sk-..."
python -m scripts.baseline_inference
```

### Issue: `pydantic validation error`

**Solution**: Check that all required fields are provided in Action:
```python
# ✗ Wrong - missing category
action = Action(action_type=ActionType.CLASSIFY)

# ✓ Correct
action = Action(
    action_type=ActionType.CLASSIFY,
    category=EmailCategory.URGENT
)
```

### Issue: `Docker build fails with "python: not found"`

**Solution**: Ensure Dockerfile uses correct Python version:
```dockerfile
FROM python:3.10-slim  # ✓ Full python installation
```

### Issue: `HF Space stays in "Building" state`

**Solution**: 
1. Check **Logs** for error messages
2. Verify Dockerfile is valid
3. Check that all files were pushed
4. Manually trigger rebuild: go to Settings → Repository → "Restart space"

---

## Performance Benchmarking

### Simple Benchmark

```python
import time
from email_triage.environment import EmailTriageEnv

# Time environment operations
env = EmailTriageEnv("task_1_easy")

# Time reset
start = time.time()
env.reset()
reset_time = time.time() - start
print(f"Reset: {reset_time*1000:.1f}ms")

# Time steps
start = time.time()
for _ in range(10):
    from email_triage.models import Action, ActionType, EmailCategory
    action = Action(action_type=ActionType.CLASSIFY, category=EmailCategory.URGENT)
    env.step(action)
step_time = (time.time() - start) / 10
print(f"Step: {step_time*1000:.1f}ms")
```

Expected results:
- `reset()`: < 10ms
- `step()`: < 5ms
- Full episode (10 steps): < 100ms

### Throughput with LLM

Baseline inference throughput:
- Per-email LLM latency: 1-5 seconds (depends on model)
- Full run (3 tasks × 10 emails): 30-150 seconds
- Network latency dominates (not environment)

---

## Continuous Integration (GitHub Actions)

Optional: Add CI/CD for automated testing

**`.github/workflows/tests.yml`**:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          python scripts/test_environment.py
      
      - name: Build Docker image
        run: |
          docker build -t email-triage-env:test .
```

Run locally to test:
```bash
# Push to GitHub, check Actions tab for results
git push origin main
```

---

## Validation Checklist

Before deployment, verify:

- [ ] All Python files pass syntax check
- [ ] `test_environment.py` passes all tests
- [ ] All Pydantic models validate correctly
- [ ] `task_1_easy` achieves > 70% with random agent
- [ ] `task_2_medium` achieves > 50% with random agent
- [ ] `task_3_hard` achieves > 40% with random agent
- [ ] Dockerfile builds without errors
- [ ] All dependencies listed in `requirements.txt`
- [ ] README is comprehensive and accurate
- [ ] `openenv.yaml` is valid YAML
- [ ] Baseline results saved to JSON successfully

---

## Quick Start Command List

```bash
# Install
pip install -r requirements.txt

# Test
python scripts/test_environment.py

# Run baseline (with API key)
export OPENAI_API_KEY="sk-..."
python -m scripts.baseline_inference

# Docker build
docker build -t email-triage-env .

# Docker test
docker run email-triage-env python scripts/test_environment.py

# Package install (development)
pip install -e .

# Python interactive
python -c "from email_triage.environment import EmailTriageEnv; print('OK')"
```

