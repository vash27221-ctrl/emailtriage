# Email Triage Environment

A real-world RL environment for training agents to classify and triage emails.
Implements the OpenEnv specification with typed Pydantic models, deterministic graders, and a hybrid RL+LLM agent powered by Groq.

---

## Overview

Agents classify incoming emails into:
- `spam` — phishing, promotions, malicious content
- `urgent` — security alerts, production incidents, time-sensitive requests
- `follow_up` — messages requiring a response or decision
- `informational` — newsletters, announcements, FYI content
- `archived` — processed/historical content

Three difficulty levels: easy → medium → hard.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Groq API key

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

### 3. Run the hybrid RL+LLM agent

```bash
python scripts/rl_agent.py
```

### 4. Run the Groq baseline only

```bash
python scripts/baseline_inference.py
```

---

## Agents

### Hybrid RL + LLM Agent (`scripts/rl_agent.py`)

Combines Q-learning with Groq LLM:

- Q-table pre-seeded with Groq labels before training
- During training: explores randomly → uses Q-table when confident → falls back to Groq when uncertain
- Groq answers are used to update Q-table (agent learns from LLM guidance)
- Over 200 episodes, LLM calls drop to ~1-5% as Q-table matures

Results:
| Task | Accuracy | Grade |
|------|----------|-------|
| task_1_easy | 90.91% | 1.00/1.0 |
| task_2_medium | 100% | 1.00/1.0 |
| task_3_hard | 90% | 1.00/1.0 |
| **Average** | | **1.00/1.0** |

### Groq Baseline (`scripts/baseline_inference.py`)

Runs Groq `llama-3.1-8b-instant` directly against all three tasks without any RL.

---

## Environment Interface

```python
from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

env = EmailTriageEnv(task_id="task_1_easy")  # or task_2_medium, task_3_hard
obs = env.reset()

done = False
while not done:
    action = Action(
        action_type=ActionType.CLASSIFY,
        category=EmailCategory.SPAM,
        reason="Obvious phishing"
    )
    obs, reward, done, info = env.step(action)
    print(f"Accuracy: {reward.accuracy:.2%}")
```

### Observation

```python
obs.current_email.sender
obs.current_email.subject
obs.current_email.preview
obs.current_email.is_reply
obs.current_email.has_attachment
obs.processed_count
obs.total_count
obs.hint  # task-specific hint
```

### Reward

```python
reward.step_reward       # 1.0 correct, 0.0 wrong
reward.cumulative_reward # running accuracy
reward.accuracy          # correct / total
```

---

## Tasks

### Task 1 — Spam Detection (Easy)
Binary: spam vs legitimate. 5 spam + 6 legitimate emails.

| Accuracy | Grade |
|----------|-------|
| ≥ 90% | 1.0 |
| 70–89% | 0.6 |
| < 70% | 0.0 |

### Task 2 — Multi-Category (Medium)
4-way: urgent / follow_up / informational / spam. 12 emails.

| Accuracy | Grade |
|----------|-------|
| ≥ 85% | 1.0 |
| 70–84% | 0.75 |
| 60–69% | 0.5 |
| < 60% | 0.25 |

### Task 3 — Edge Cases (Hard)
10 ambiguous emails where category boundaries blur.

| Accuracy | Grade |
|----------|-------|
| ≥ 90% | 1.0 |
| 80–89% | 0.8 |
| 70–79% | 0.6 |
| 60–69% | 0.3 |
| < 60% | 0.0 |

---

## File Structure

```
email-triage-env/
├── email_triage/
│   ├── environment.py       # EmailTriageEnv (reset, step, state)
│   ├── models.py            # Pydantic models (Action, Observation, Reward)
│   ├── openenv_spec.py      # OpenEnv spec & validation
│   └── tasks/
│       ├── base_task.py     # Abstract Task base class
│       └── implementations.py  # Easy / Medium / Hard tasks
├── scripts/
│   ├── rl_agent.py          # Hybrid RL+LLM agent (main entry point)
│   ├── baseline_inference.py   # Groq-only baseline
│   └── test_environment.py  # Environment sanity checks
├── examples.py              # Usage examples
├── openenv.yaml             # OpenEnv spec
├── requirements.txt
├── setup.py
├── Dockerfile
└── README.md
```

---

## Adding a Custom Task

1. Subclass `Task` in `email_triage/tasks/implementations.py`:

```python
class MyTask(Task):
    def __init__(self):
        super().__init__(task_id="task_4_custom", description="...", difficulty="hard")

    def generate_emails(self) -> List[Email]:
        ...

    def grade(self) -> float:
        accuracy = self.correct_count / self.total_processed
        return 1.0 if accuracy >= 0.9 else 0.0
```

2. Register in `email_triage/tasks/__init__.py`:

```python
AVAILABLE_TASKS["task_4_custom"] = MyTask
```

---

## License

MIT
