---
title: Email Triage Env
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Email Triage Environment

Hybrid RL + LLM agent for email classification. Submission for Meta PyTorch OpenEnv Hackathon x Scaler School of Technology, Round 1.

## Results

| Task | Score | Accuracy |
|------|-------|----------|
| task_1_easy (Spam Detection) | 0.990 | 100% |
| task_2_medium (Multi-Category) | 0.990 | 100% |
| task_3_hard (Edge Cases) | 0.990 | 100% |
| **Average** | **0.990** | |

## Architecture

Hybrid Q-learning + LLM agent:

1. **Preseed** — LLM labels all emails once to initialize Q-table with strong priors
2. **RL Training** — 50 episodes of epsilon-greedy Q-learning refine the Q-table
3. **Evaluation** — greedy policy using Q-table, LLM fallback for uncertain states

The agent reduces LLM calls over time as the Q-table matures.

## Environment

Three difficulty levels:

- **task_1_easy** — Spam vs legitimate (spam / follow_up / informational / urgent), 11 emails
- **task_2_medium** — 4-way classification with mixed signals, 12 emails
- **task_3_hard** — Edge cases and ambiguous emails, 10 emails

## Quick Start

### 1. Set environment variables

```bash
export HF_TOKEN=your_groq_api_key
export API_BASE_URL=https://api.groq.com/openai/v1   # default
export MODEL_NAME=llama-3.1-8b-instant               # default
```

Or create a `.env` file:

```
GROQ_API_KEY=your_key_here
HF_TOKEN=your_key_here
```

### 2. Install dependencies

```bash
pip install -r email-triage-env/requirements.txt
```

### 3. Run inference

```bash
python3 inference.py
```

### 4. Run the REST server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Output Format

```
[START] task=task_1_easy env=email-triage model=llama-3.1-8b-instant
[STEP] step=1 action=classify('spam') reward=0.99 done=false error=null
...
[END] success=true steps=11 score=0.990 rewards=0.99,0.99,...
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/reset` | POST | Reset environment, returns initial observation |
| `/step` | POST | Take action, returns observation + reward |
| `/state` | GET | Current state snapshot |

## File Structure

```
├── inference.py          # Hackathon submission script (RL+LLM agent)
├── server/app.py         # FastAPI REST server
├── app.py                # Alternative server entry point
├── Dockerfile            # Docker container config
└── email-triage-env/
    ├── email_triage/
    │   ├── environment.py      # EmailTriageEnv
    │   ├── models.py           # Pydantic models
    │   └── tasks/
    │       ├── base_task.py    # Abstract Task
    │       └── implementations.py  # Easy/Medium/Hard tasks
    └── scripts/
        ├── rl_agent.py         # Full RL+LLM training script
        └── baseline_inference.py   # LLM-only baseline
```
