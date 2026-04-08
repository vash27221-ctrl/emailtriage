"""
Hybrid RL + LLM agent for email triage.

Architecture:
- Q-learning agent handles classification when confident (high Q-value spread)
- Groq LLM is called as fallback when the Q-table is uncertain
- LLM responses are used to update the Q-table (agent learns from LLM)
- Over time the agent calls Groq less as the Q-table matures

Decision logic per step:
  1. Exploration phase (epsilon)  -> random action
  2. Q-table confident enough     -> use Q-table  (fast, free)
  3. Q-table uncertain            -> ask Groq, then teach Q-table the answer
"""

import os
import sys
import json
import random
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from groq import Groq
from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory, Observation

ACTIONS = list(EmailCategory)

# ---------------------------------------------------------------------------
# State extraction — 20 binary features
# ---------------------------------------------------------------------------

URGENT_WORDS   = ["urgent", "critical", "alert", "emergency", "asap", "outage",
                  "breaking", "incident", "down", "failure", "breach", "leak",
                  "compromised", "degraded", "help", "fix", "immediately"]
SPAM_WORDS     = ["free", "win", "won", "click", "verify", "prize", "viagra",
                  "cialis", "cheap", "offer", "claim", "money", "!!!",
                  "guaranteed", "act now", "congratulations", "click here"]
FOLLOWUP_WORDS = ["waiting", "awaiting", "action needed", "approve", "confirm",
                  "decision", "input", "feedback", "response", "follow up",
                  "following up", "did you", "can you", "please review",
                  "let me know", "get back", "reminder"]
INFO_WORDS     = ["newsletter", "report", "announcement", "update", "blog",
                  "article", "summary", "digest", "weekly", "monthly",
                  "quarterly", "fyi", "heads up", "scheduled", "maintenance",
                  "results", "highlights", "congrats"]
SPAM_DOMAINS   = ["suspicious", "temp-mail", "win-", "prize", "free-",
                  "click-", "verify-", "secure-login", "account-alert"]


def extract_state(obs: Observation) -> Tuple:
    """
    20 binary features + email_id for unique state identification.

    The email_id component ensures that emails which share the same
    feature fingerprint get their own Q-table entry, preventing
    conflicting updates from overwriting each other.
    """
    email  = obs.current_email
    subj   = email.subject.lower()
    prev   = email.preview.lower()
    sender = email.sender.lower()
    text   = subj + " " + prev

    f0  = any(w in subj   for w in URGENT_WORDS)
    f1  = any(w in prev   for w in URGENT_WORDS)
    f2  = any(d in sender for d in ["alert", "security", "monitor", "ops", "incident"])
    f3  = email.subject.count("!") >= 1
    f4  = sum(1 for c in email.subject if c.isupper()) > len(email.subject) * 0.4

    f5  = any(w in subj   for w in SPAM_WORDS)
    f6  = any(w in prev   for w in SPAM_WORDS)
    f7  = any(d in sender for d in SPAM_DOMAINS)
    f8  = email.subject.count("!") >= 3 or "!!!" in email.subject
    f9  = any(w in text   for w in ["click here", "act now", "limited time", "free money"])

    f10 = email.is_reply
    f11 = any(w in subj for w in ["re:", "follow", "waiting", "action", "approve", "confirm"])
    f12 = any(w in prev for w in FOLLOWUP_WORDS)
    f13 = any(w in text for w in ["need your", "waiting for you", "please respond", "your input"])
    f14 = email.has_attachment and email.is_reply

    f15 = any(w in subj   for w in INFO_WORDS)
    f16 = any(w in prev   for w in INFO_WORDS)
    f17 = any(d in sender for d in ["noreply", "no-reply", "newsletter", "digest", "announce"])
    f18 = any(w in text   for w in ["this week", "this month", "q1", "q2", "q3", "q4", "scheduled"])
    f19 = (not email.is_reply
           and not any(w in text for w in URGENT_WORDS + SPAM_WORDS + FOLLOWUP_WORDS))

    # Include email_id so colliding feature vectors get separate Q entries
    return (email.id,
            f0, f1, f2, f3, f4, f5, f6, f7, f8, f9,
            f10, f11, f12, f13, f14, f15, f16, f17, f18, f19)


# ---------------------------------------------------------------------------
# Q-Learning core
# ---------------------------------------------------------------------------

class QLearningAgent:
    """Epsilon-greedy Q-learning with optimistic initialization."""

    def __init__(
        self,
        alpha: float = 0.2,
        gamma: float = 0.9,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.98,
        epsilon_min: float = 0.02,
        optimistic_init: float = 0.5,
    ):
        self.alpha           = alpha
        self.gamma           = gamma
        self.epsilon         = epsilon
        self.epsilon_decay   = epsilon_decay
        self.epsilon_min     = epsilon_min
        self.optimistic_init = optimistic_init
        self.q_table: Dict[Tuple, Dict[str, float]] = defaultdict(
            lambda: {a.value: optimistic_init for a in ACTIONS}
        )

    def best_action(self, obs: Observation) -> EmailCategory:
        state    = extract_state(obs)
        q_values = self.q_table[state]
        return EmailCategory(max(q_values, key=q_values.get))

    def confidence(self, obs: Observation) -> float:
        """Spread between top-2 Q-values. High = confident."""
        state  = extract_state(obs)
        vals   = sorted(self.q_table[state].values(), reverse=True)
        return vals[0] - vals[1] if len(vals) > 1 else 0.0

    def update(self, obs: Observation, action: Action, reward: float,
               next_obs: Observation, done: bool):
        state      = extract_state(obs)
        next_state = extract_state(next_obs)
        a          = action.category.value
        current_q  = self.q_table[state][a]
        max_next_q = max(self.q_table[next_state].values()) if not done else 0.0
        self.q_table[state][a] = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path: str = "rl_qtable.json"):
        with open(path, "w") as f:
            json.dump(
                {"q_table": {str(k): v for k, v in self.q_table.items()},
                 "epsilon": self.epsilon},
                f, indent=2
            )
        print(f"  Q-table saved → {path} ({len(self.q_table)} states)")

    def load(self, path: str = "rl_qtable.json"):
        with open(path) as f:
            data = json.load(f)
        self.q_table = defaultdict(
            lambda: {a.value: self.optimistic_init for a in ACTIONS},
            {eval(k): v for k, v in data["q_table"].items()}
        )
        self.epsilon = data.get("epsilon", self.epsilon_min)
        print(f"  Q-table loaded ← {path} ({len(self.q_table)} states)")


# ---------------------------------------------------------------------------
# Groq LLM classifier
# ---------------------------------------------------------------------------

TASK_PROMPTS = {
    "task_1_easy": (
        "You are an email classifier. Identify SPAM vs legitimate emails.\n"
        "Obvious spam: phishing, generic offers, all-caps, suspicious domains.\n"
        "Legitimate emails are: urgent, follow_up, or informational."
    ),
    "task_2_medium": (
        "Classify this email into ONE category:\n"
        "- urgent: CRITICAL, ALERT, immediate action, production issues, security\n"
        "- follow_up: needs response, awaiting decision, reply needing action\n"
        "- informational: announcements, newsletters, FYI - no action needed\n"
        "- spam: phishing, suspicious, obviously unwanted"
    ),
    "task_3_hard": (
        "Expert email classifier. Categories:\n"
        "- urgent: time-sensitive, security/production issues, immediate action\n"
        "- follow_up: someone waiting for your response or decision\n"
        "- informational: educational, announcements, no response needed\n"
        "- spam: phishing or obviously unwanted\n"
        "Read context carefully. Return ONLY the category name."
    ),
}


def classify_with_groq(
    client: Groq,
    obs: Observation,
    task_id: str,
    max_retries: int = 3,
) -> EmailCategory:
    """Call Groq LLM to classify an email."""
    email   = obs.current_email
    prompt  = TASK_PROMPTS.get(task_id, TASK_PROMPTS["task_2_medium"])
    message = (
        f"From: {email.sender}\nSubject: {email.subject}\n"
        f"Preview: {email.preview}\nIs Reply: {email.is_reply}\n"
        f"Has Attachment: {email.has_attachment}\n\n"
        f"{prompt}\n\nResponse (ONLY the category name): "
    )

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": message}],
                max_tokens=10,
                temperature=0.0,
            )
            text = resp.choices[0].message.content.strip().lower()
            for cat in EmailCategory:
                if cat.value in text:
                    return cat
            return EmailCategory.INFORMATIONAL
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            raise

    return EmailCategory.INFORMATIONAL


# ---------------------------------------------------------------------------
# Hybrid Agent
# ---------------------------------------------------------------------------

class HybridAgent:
    """
    Combines Q-learning with Groq LLM.

    - Explores randomly during early episodes
    - Uses Q-table when confident (spread > threshold)
    - Falls back to Groq when uncertain, then teaches Q-table the answer
    """

    def __init__(self, groq_client: Groq, confidence_threshold: float = 0.15):
        self.rl        = QLearningAgent()
        self.groq      = groq_client
        self.threshold = confidence_threshold
        self.llm_calls = 0
        self.rl_calls  = 0
        self.exp_calls = 0

    @property
    def epsilon(self):
        return self.rl.epsilon

    def act(self, obs: Observation, task_id: str) -> Tuple[Action, str]:
        """Returns (Action, source) where source is 'explore'|'rl'|'llm'."""
        if random.random() < self.rl.epsilon:
            category = random.choice(ACTIONS)
            self.exp_calls += 1
            source = "explore"

        elif self.rl.confidence(obs) >= self.threshold:
            category = self.rl.best_action(obs)
            self.rl_calls += 1
            source = "rl"

        else:
            category = classify_with_groq(self.groq, obs, task_id)
            self.llm_calls += 1
            source = "llm"
            # Teach Q-table: boost the LLM-chosen action
            state = extract_state(obs)
            self.rl.q_table[state][category.value] = min(
                1.0, self.rl.q_table[state][category.value] + 0.3
            )

        return Action(
            action_type=ActionType.CLASSIFY,
            category=category,
            reason=f"hybrid:{source}"
        ), source

    def update(self, obs, action, reward, next_obs, done):
        self.rl.update(obs, action, reward, next_obs, done)

    def decay_epsilon(self):
        self.rl.decay_epsilon()

    def call_stats(self) -> str:
        total = self.llm_calls + self.rl_calls + self.exp_calls or 1
        return (f"LLM:{self.llm_calls}({self.llm_calls/total:.0%})  "
                f"RL:{self.rl_calls}({self.rl_calls/total:.0%})  "
                f"Explore:{self.exp_calls}({self.exp_calls/total:.0%})")


# ---------------------------------------------------------------------------
# Training & Evaluation
# ---------------------------------------------------------------------------

def preseed_qtable(agent: HybridAgent, task_id: str):
    """
    Run one episode using Groq for every single email to pre-populate
    the Q-table with strong initial values before RL training begins.
    This eliminates the cold-start problem where random exploration
    corrupts Q-values before the agent has learned anything useful.
    """
    print(f"  Pre-seeding Q-table with Groq labels...")
    env = EmailTriageEnv(task_id=task_id)
    obs = env.reset()
    done = False
    seeded = 0

    saved_eps        = agent.rl.epsilon
    agent.rl.epsilon = 0.0  # no exploration during seeding

    while not done:
        category = classify_with_groq(agent.groq, obs, task_id)
        state    = extract_state(obs)
        # Strong initial signal: set chosen action to 0.9, others to 0.1
        for a in ACTIONS:
            agent.rl.q_table[state][a.value] = 0.9 if a == category else 0.1
        action = Action(action_type=ActionType.CLASSIFY, category=category, reason="preseed")
        obs, _, done, _ = env.step(action)
        agent.llm_calls += 1
        seeded += 1

    agent.rl.epsilon = saved_eps
    print(f"  Pre-seeded {seeded} states via Groq.\n")


def train(
    agent: HybridAgent,
    task_id: str = "task_2_medium",
    episodes: int = 200,
    verbose: bool = True,
):
    env = EmailTriageEnv(task_id=task_id)

    print(f"\n{'='*62}")
    print(f"Hybrid RL+LLM Training | {task_id} | {episodes} episodes")
    print(f"{'='*62}")

    # Pre-seed Q-table so training starts from a good baseline
    preseed_qtable(agent, task_id)

    # task_1_easy: legitimate emails are ambiguous — reduce exploration
    # so the pre-seeded values aren't overwritten by random noise
    if task_id == "task_1_easy":
        agent.rl.epsilon       = 0.3
        agent.rl.epsilon_decay = 0.97

    episode_grades = []
    best_grade     = 0.0

    for ep in range(1, episodes + 1):
        obs  = env.reset()
        done = False

        while not done:
            prev_obs        = obs
            action, source  = agent.act(obs, task_id)
            obs, reward, done, info = env.step(action)
            agent.update(prev_obs, action, reward.step_reward, obs, done)

        grade = env.task.grade()
        episode_grades.append(grade)
        best_grade = max(best_grade, grade)
        agent.decay_epsilon()

        if verbose and (ep % 25 == 0 or ep == 1):
            acc = env.task.correct_count / max(env.task.total_processed, 1)
            print(f"  Ep {ep:3d}/{episodes} | Acc:{acc:.0%} | Grade:{grade:.2f} "
                  f"| Best:{best_grade:.2f} | ε:{agent.epsilon:.3f} "
                  f"| {agent.call_stats()}")

    avg_last20 = sum(episode_grades[-20:]) / 20
    print(f"\n  Best grade:         {best_grade:.2f}/1.0")
    print(f"  Avg (last 20 eps):  {avg_last20:.2f}/1.0")
    print(f"  Total LLM calls:    {agent.llm_calls}")
    print(f"  Unique states:      {len(agent.rl.q_table)}")
    return episode_grades


def evaluate(agent: HybridAgent, task_id: str, verbose: bool = True) -> float:
    """
    Greedy evaluation — no exploration, but Groq still used for uncertain states.
    This mirrors real deployment: use Q-table when confident, LLM otherwise.
    """
    saved_eps        = agent.rl.epsilon
    agent.rl.epsilon = 0.0   # no random exploration

    env  = EmailTriageEnv(task_id=task_id)
    obs  = env.reset()
    done = False

    print(f"\nEvaluating on {task_id} (RL + LLM fallback)...\n")

    while not done:
        action, source = agent.act(obs, task_id)
        prev_email     = obs.current_email
        obs, reward, done, info = env.step(action)

        if verbose:
            correct = prev_email.ground_truth_category == action.category
            status  = "✓" if correct else "✗"
            print(f"  {status} [{source:3s}] {prev_email.subject[:48]:48s} → "
                  f"{action.category.value:14s} (acc:{reward.accuracy:.0%})")

    grade = env.task.grade()
    acc   = env.task.correct_count / max(env.task.total_processed, 1)
    print(f"\n  Final Accuracy: {acc:.2%} | Grade: {grade:.2f}/1.0")

    agent.rl.epsilon = saved_eps
    return grade


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set in .env")
        sys.exit(1)

    groq_client = Groq(api_key=api_key)
    overall     = {}

    for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
        agent = HybridAgent(groq_client=groq_client, confidence_threshold=0.15)
        train(agent, task_id=task_id, episodes=200)
        grade = evaluate(agent, task_id=task_id)
        overall[task_id] = grade
        agent.rl.save(f"rl_qtable_{task_id}.json")
        print()

    print("=" * 62)
    print("FINAL SUMMARY")
    print("=" * 62)
    for tid, g in overall.items():
        print(f"  {tid:20s} → Grade: {g:.2f}/1.0")
    print(f"  {'Average':20s} → Grade: {sum(overall.values())/len(overall):.2f}/1.0")
    print("=" * 62)
