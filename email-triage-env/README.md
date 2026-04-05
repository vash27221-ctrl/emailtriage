# Email Triage Environment (OpenEnv)

A production-ready, real-world environment for training and evaluating AI agents to automatically classify and triage emails. This environment implements the full OpenEnv specification with typed models, deterministic graders, and meaningful reward signals.

## Overview

**Problem**: In modern workplaces, employees are overwhelmed by email volume. Important messages (security alerts, urgent client requests) can be lost among informational updates and spam. Effective email triage is both a real human problem and an economically important task.

**Solution**: Train AI agents to classify incoming emails into intelligible categories:
- **SPAM**: Phishing attempts, unwanted promotions, obviously malicious content
- **URGENT**: Security alerts, production incidents, time-sensitive business requests
- **FOLLOW_UP**: Messages requiring the user's response or decision
- **INFORMATIONAL**: Newsletters, announcements, FYI content (no action needed)
- **ARCHIVED**: Processed, historical content

Agents receive partial credit for correct classifications, creating a smooth learning signal across difficulty levels.

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- OpenAI API key (Claude available via Anthropic)

### 2. Installation

```bash
git clone https://github.com/your-repo/email-triage-env.git
cd email-triage-env

pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Run Baseline

```bash
python -m scripts.baseline_inference
```

This runs the OpenAI API client against all three tasks and produces:
- Per-task accuracy metrics
- Task-specific grades (0.0-1.0)
- Average performance score
- Detailed results saved to `baseline_results.json`

---

## Environment Specification

### Action Space

```python
class Action(BaseModel):
    action_type: ActionType  # "classify", "read_more", "flag", "archive", "skip"
    category: Optional[EmailCategory]  # "spam", "urgent", "follow_up", "informational"
    reason: Optional[str]  # Agent's reasoning
```

**Primary action**: `CLASSIFY` with a category. Other actions receive penalties.

### Observation Space

```python
class Observation(BaseModel):
    current_email: Email  # Sender, subject, preview, metadata
    processed_count: int  # Emails processed so far
    total_count: int  # Total emails in batch
    correct_classifications: int  # Running count
    task_id: str  # Which task running
    hint: Optional[str]  # Task-specific hint (e.g., "Check for urgent keywords")
```

Email metadata provided:
- `sender`: Email address
- `subject`: Subject line
- `preview`: Body preview (first ~100 chars)
- `received_time`: ISO timestamp
- `is_reply`: Boolean flag
- `has_attachment`: Boolean flag

### Reward Signal

```python
class Reward(BaseModel):
    step_reward: float  # 0.0 or 1.0 for this step
    cumulative_reward: float  # Running accuracy
    accuracy: float  # Correct / Total processed
    bonus: float  # Extra reward for exceptional performance
    penalty: float  # Penalty for errors
```

**Reward structure**:
- Correct classification: `+1.0` step reward
- Incorrect classification: `0.0` step reward
- Non-classification actions: `-0.1` penalty
- Cumulative reward normalizes to [0, 1] representing overall accuracy

---

## Tasks

### Task 1: Spam Detection (Easy)
**Objective**: Binary classification: SPAM vs. legitimate emails  
**Difficulty**: Easy - obvious spam signals

**Dataset**:
- 5 obvious spam emails (phishing, viagra ads, fake prize claims)
- 6 legitimate business emails

**Grading**:
| Accuracy | Grade |
|----------|-------|
| ≥ 90% | 1.0 ✓ |
| 70-89% | 0.6 |
| < 70% | 0.0 ✗ |

**Hints provided**: Spam keywords, suspicious domains, ALL-CAPS, multiple exclamation marks

**Why this matters**: Spam filters are first-line defense. This task ensures agents learn obvious danger signals.

---

### Task 2: Multi-Category Classification (Medium)
**Objective**: 4-way classification (URGENT, FOLLOW_UP, INFORMATIONAL, implicit SPAM)  
**Difficulty**: Medium - mixed signals, some ambiguity

**Dataset**:
- 3 urgent emails (production issues, security alerts, client emergencies)
- 3 follow-up emails (replies awaiting decisions)
- 3 informational emails (newsletters, announcements)
- 3 ambiguous emails (could be follow-up OR informational)

Total: 12 emails, 9 clear + 3 challenging

**Grading**:
| Accuracy | Grade |
|----------|-------|
| ≥ 85% | 1.0 |
| 70-84% | 0.75 |
| 60-69% | 0.5 |
| < 60% | 0.25 |

**Hints provided**: Contextual clues about category-specific patterns without spoiling answers

**Why this matters**: Real inbox management requires distinguishing between similar categories. This is where agents need to reason about context.

---

### Task 3: Edge Cases & Ambiguity (Hard)
**Objective**: Complex classification with adversarial examples  
**Difficulty**: Hard - similar categories, must reason carefully

**Dataset**:
- 10 carefully crafted emails where category boundaries blur
- Examples:
  - "Fix bug before release" → URGENT (production risk) vs. FOLLOW_UP (asking for action)
  - "Thanks for review" → FOLLOW_UP (conversation) vs. INFORMATIONAL (acknowledgment)
  - "System degraded - investigating" → URGENT (alert) vs. INFORMATIONAL (FYI on status)

**Grading**:
| Accuracy | Grade | Interpretation |
|----------|-------|-----------------|
| ≥ 90% | 1.0 | Expert-level |
| 80-89% | 0.8 | Proficient |
| 70-79% | 0.6 | Competent |
| 60-69% | 0.3 | Minimal competence |
| < 60% | 0.0 | Failure |

**Hints**: Strategic without eliminating ambiguity (e.g., "Could be FOLLOW_UP - analyze if waiting for user response")

**Why this matters**: In real email triage, most difficulty comes from edge cases. High performance here indicates genuine understanding, not memorization.

---

## Deterministic Task Graders

Each task has a **deterministic, auditable grader** that:

1. **Computes accuracy** = (correct_classifications / total_processed)
2. **Maps accuracy to grade** via task-specific rubric
3. **Provides clear thresholds** (no black-box scoring)
4. **Returns exactly 0.0-1.0** so agent performance is comparable across tasks

Graders are implemented in `email_triage/tasks/implementations.py`:

```python
def grade(self) -> float:
    accuracy = self.correct_count / self.total_processed
    if accuracy >= 0.90:
        return 1.0
    elif accuracy >= 0.70:
        return 0.6
    else:
        return 0.0
```

---

## Environment Interface (OpenEnv Compliance)

### Initialization
```python
from email_triage.environment import EmailTriageEnv

env = EmailTriageEnv(task_id="task_1_easy")
```

Available task_ids:
- `task_1_easy`
- `task_2_medium`
- `task_3_hard`

### Episode Loop
```python
observation = env.reset()

done = False
while not done:
    action = agent.act(observation)
    observation, reward, done, info = env.step(action)
```

### Access Complete State
```python
state = env.state()  # StateSnapshot with full episode history
print(state.emails_processed)  # List of (email_id, predicted, ground_truth)
print(state.cumulative_reward)  # Final accuracy
```

---

## Baseline Inference Script

**File**: `scripts/baseline_inference.py`

Uses OpenAI Anthropic Claude to classify emails. Demonstrates:
- Integration with real LLM API
- Reproducible baseline scores
- Proper error handling
- Detailed per-email logging

### Running

```bash
export OPENAI_API_KEY="sk-..."
python -m scripts.baseline_inference
```

### Output

```
============================================================
Running Baseline on task_1_easy
============================================================
Task: Detect obvious spam emails
Difficulty: easy
Total emails: 11

✓ Step 1: YOU HAVE WON! Claim your prize now!!!     → spam         (acc: 100.00%)
✓ Step 2: Project Alpha: Q1 Status Update           → urgent       (acc: 100.00%)
...

============================================================
Results for task_1_easy
============================================================
Accuracy: 90.91% (10/11)
Final Grade: 1.0/1.0
============================================================

FINAL SUMMARY
============================================================
task_1_easy    : Accuracy  90.91% | Grade  1.00/1.0
task_2_medium  : Accuracy  83.33% | Grade  0.75/1.0
task_3_hard    : Accuracy  80.00% | Grade  0.80/1.0
-----
Average Grade: 0.82/1.0
============================================================
```

Results saved to `baseline_results.json` with detailed per-email metrics.

---

## Reward Function Design

The reward function provides **meaningful, partial progress signals**:

### Step-level Reward
- **+1.0** for correct classification
- **0.0** for incorrect classification
- **-0.1** penalty for non-classification actions

### Cumulative Reward
- Normalized accuracy: correct_count / total_processed
- Ranges from 0.0 (all wrong) to 1.0 (all correct)
- Updated every step to show progress

### Why This Design?

1. **Immediate feedback**: Agent knows instantly if classification was correct
2. **Progress signal**: Cumulative reward shows trending accuracy without waiting for episode end
3. **Penalizes procrastination**: Avoiding classification (READ_MORE, SKIP) loses reward
4. **Future-friendly**: Reward signal supports both RL and supervised baselines

---

## Deployment to Hugging Face Spaces

### 1. Create HF Space

```bash
# Go to huggingface.co/spaces and create new space
# Select: Docker, select repository
```

### 2. Push Code

```bash
git clone https://huggingface.co/spaces/your-username/email-triage-env
cd email-triage-env

# Copy files
cp -r ../email-triage-env/* .

# Push to HF
git add .
git commit -m "Initial commit"
git push origin main
```

### 3. Configure Secrets

In HF Space settings, add secrets:
- `OPENAI_API_KEY`: Your API key
- Make sure it's marked as "Private"

### 4. Build & Deploy

HF Spaces auto-builds from Dockerfile. After ~5-10 min, your space goes live.

### 5. Access

- View results at: `https://huggingface.co/spaces/your-username/email-triage-env`
- Space runs baseline every time it starts
- Results visible in space logs

---

## Local Development & Testing

### Run Single Task

```python
from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

env = EmailTriageEnv(task_id="task_1_easy")
obs = env.reset()

# Manually classify first email
action = Action(
    action_type=ActionType.CLASSIFY,
    category=EmailCategory.SPAM,
    reason="Obvious phishing"
)

obs, reward, done, info = env.step(action)
print(f"Accuracy: {reward.accuracy:.2%}")
print(f"Grade (if done): {info.get('final_grade', 'N/A')}")
```

### Validate OpenEnv Spec

```bash
python -c "from email_triage.openenv_spec import validate_environment_spec; validate_environment_spec()"
```

### Docker Build Locally

```bash
docker build -t email-triage-env .
docker run -e OPENAI_API_KEY="your-key" email-triage-env
```

---

## File Structure

```
email-triage-env/
├── email_triage/
│   ├── __init__.py
│   ├── models.py           # Pydantic models (Action, Observation, Reward, etc.)
│   ├── environment.py      # Main EmailTriageEnv class
│   ├── openenv_spec.py     # OpenEnv specification & validation
│   └── tasks/
│       ├── __init__.py
│       ├── base_task.py    # Task base class
│       └── implementations.py  # Easy/Medium/Hard tasks
├── scripts/
│   └── baseline_inference.py  # OpenAI API baseline
├── openenv.yaml            # OpenEnv spec (YAML)
├── requirements.txt        # Dependencies
├── Dockerfile              # HF Spaces deployment
└── README.md              # This file
```

---

## Implementation Details

### Typed Models (Pydantic v2)

All core types are Pydantic v2 models with full validation:

```python
class Observation(BaseModel):
    current_email: Email
    processed_count: int = Field(ge=0, description="...")
    hint: Optional[str] = None
```

Benefits:
- IDE autocomplete & type checking
- JSON serialization/deserialization
- Runtime validation
- Schema generation for API

### Task Graders

Each task implements `grade() -> float` with clear rubric:
- Easy: 90%+ → 1.0, else scaled
- Medium: 85%+ → 1.0, with graduated scale
- Hard: 90%+ → 1.0, with lower floor (0.0 for <60%)

Graders are **deterministic and auditable**.

### Reward Shaping

Rewards are shaped to encourage:
1. **High accuracy** (primary metric)
2. **Fast task completion** (cumulative reward encourages action)
3. **Reasonable behavior** (penalties for skipping)

---

## Extending the Environment

### Add a New Task

1. Create subclass in `email_triage/tasks/implementations.py`:

```python
class CustomTask(Task):
    def __init__(self):
        super().__init__(
            task_id="task_4_custom",
            description="Your task description",
            difficulty="hard"
        )
    
    def generate_emails(self) -> List[Email]:
        # Return list of Email objects
        pass
    
    def grade(self) -> float:
        # Implement grading rubric
        pass
```

2. Register in `email_triage/tasks/__init__.py`:

```python
AVAILABLE_TASKS["task_4_custom"] = CustomTask
```

3. Update `openenv.yaml` with new task metadata

### Add a Custom Agent

```python
from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

class MyAgent:
    def act(self, observation):
        # Implement your classification logic
        return Action(
            action_type=ActionType.CLASSIFY,
            category=EmailCategory.URGENT,
            reason="My reasoning"
        )

env = EmailTriageEnv(task_id="task_1_easy")
obs = env.reset()
done = False

while not done:
    action = agent.act(obs)
    obs, reward, done, info = env.step(action)
```

---

## Metrics & Evaluation

### Per-Task Metrics

- **Accuracy**: correct / total
- **Grade**: 0.0-1.0 via rubric
- **Per-email correctness**: logged in `info["performance"]`

### Aggregate Metrics

- **Average grade** across all tasks: (grade_easy + grade_medium + grade_hard) / 3
- **Aggregate accuracy** (optional): weighted average by difficulty

### Reproducibility

All metrics are **deterministic**:
- Same emails generated each `reset()`
- Same grading rubric applied
- Reward calculation is identical across runs

For reproducible baselines, set random seed at script start:

```python
import random
random.seed(42)
```

---

## Future Enhancements

- [ ] Variable dataset size (batch of 5, 10, 20+ emails)
- [ ] Multi-agent evaluation (competition mode)
- [ ] Time-based pressure (reward decreases over time)
- [ ] Real email corpus (Enron dataset, anonymized)
- [ ] Domain adaptation (medical, legal, finance email styles)
- [ ] Explanation requirement (agent must provide reasoning)

---

## References

- **OpenEnv**: https://github.com/openenv-team/openenv
- **Pydantic**: https://docs.pydantic.dev/
- **OpenAI API**: https://platform.openai.com/
- **Hugging Face Spaces**: https://huggingface.co/spaces

---

## License

MIT

---

## Contributing

PRs welcome! Please ensure:
1. All existing tests pass
2. Clear commit messages
3. Updated README if changing behavior
4. New tasks include grader implementation

---

## Acknowledgments

This environment was designed following real-world email triage challenges and OpenEnv specification best practices.
