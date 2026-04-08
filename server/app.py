"""
OpenEnv FastAPI server for Email Triage environment.
Entry point: server.app:main (referenced in pyproject.toml [project.scripts])
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "email-triage-env"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

app = FastAPI(
    title="Email Triage OpenEnv",
    description="Hybrid RL+LLM email classification environment",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_env: Optional[EmailTriageEnv] = None


class ResetRequest(BaseModel):
    task_id: Optional[str] = "task_1_easy"


class StepRequest(BaseModel):
    action: str
    category: Optional[str] = None


def parse_category(action_str: str) -> EmailCategory:
    action_str = action_str.lower()
    for cat in EmailCategory:
        if cat.value in action_str:
            return cat
    return EmailCategory.INFORMATIONAL


def obs_to_dict(obs) -> Dict[str, Any]:
    email = obs.current_email
    return {
        "current_email": {
            "id": email.id,
            "sender": email.sender,
            "subject": email.subject,
            "preview": email.preview,
            "received_time": email.received_time,
            "is_reply": email.is_reply,
            "has_attachment": email.has_attachment,
        },
        "processed_count": obs.processed_count,
        "total_count": obs.total_count,
        "correct_classifications": obs.correct_classifications,
        "task_id": obs.task_id,
        "hint": obs.hint,
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "email-triage-env"}


@app.post("/reset")
def reset(request: ResetRequest = None):
    global _env
    task_id = request.task_id if request and request.task_id else "task_1_easy"
    _env = EmailTriageEnv(task_id=task_id)
    obs = _env.reset()
    return {"observation": obs_to_dict(obs), "task_id": task_id, "status": "reset_ok"}


@app.post("/step")
def step(request: StepRequest):
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first.")
    category = (
        EmailCategory(request.category.lower())
        if request.category
        else parse_category(request.action)
    )
    action = Action(action_type=ActionType.CLASSIFY, category=category, reason=request.action)
    obs, reward, done, info = _env.step(action)
    return {
        "observation": obs_to_dict(obs),
        "reward": reward.step_reward,
        "done": done,
        "info": {"accuracy": reward.accuracy, "cumulative_reward": reward.cumulative_reward},
    }


@app.get("/state")
def state():
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first.")
    s = _env.state()
    return {
        "task_id": s.task_id,
        "episode_step": s.episode_step,
        "total_correct": s.total_correct,
        "total_wrong": s.total_wrong,
        "cumulative_reward": s.cumulative_reward,
    }


@app.get("/")
def root():
    return {"service": "email-triage-env", "status": "running",
            "endpoints": ["/health", "/reset", "/step", "/state"]}


def main():
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
