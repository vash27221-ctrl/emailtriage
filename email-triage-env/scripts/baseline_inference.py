"""Baseline inference script using OpenAI API."""

import os
import json
import sys
from typing import Dict, Any
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


def load_api_key() -> str:
    """Load OpenAI API key from environment (.env or environment variables)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Please set it before running: export OPENAI_API_KEY='your-key'"
        )
    return api_key


def classify_email_with_gpt(
    client: OpenAI,
    sender: str,
    subject: str,
    preview: str,
    is_reply: bool,
    has_attachment: bool,
    task_id: str,
) -> EmailCategory:
    """
    Use GPT to classify an email.
    
    Args:
        client: OpenAI client
        sender: Email sender address
        subject: Email subject line
        preview: Email body preview
        is_reply: Whether this is a reply
        has_attachment: Whether email has attachments
        task_id: Task ID for context
    
    Returns:
        Predicted email category
    """
    
    # Build task-specific prompt
    task_prompts = {
        "task_1_easy": """You are an email classification AI. Your task is to identify SPAM emails.
Return ONLY ONE category: spam or urgent/follow_up/informational (for legitimate emails).
Obvious spam has: phishing attempts, generic offers, all-caps headers, suspicious domains.""",
        
        "task_2_medium": """Classify this email into ONE of these categories:
- urgent: CRITICAL, ALERT, immediate action, production issues, security incidents
- follow_up: Requires response, asks for decision, awaiting input, is a reply needing action
- informational: Announcements, newsletters, updates, FYI content - no action needed
- spam: Phishing, suspicious, obviously spam
Pick the MOST appropriate category.""",
        
        "task_3_hard": """You are an expert email classifier. Analyze context carefully.
Categories:
- urgent: Time-sensitive, security/production issues, needs immediate action
- follow_up: Person waiting for your response/decision
- informational: Educational, announcements, no response needed
- spam: Phishing or obviously unwanted

These can be VERY similar. Read the FULL context. Return ONLY the category name.""",
    }
    
    task_prompt = task_prompts.get(
        task_id,
        "Classify this email into: spam, urgent, follow_up, or informational"
    )
    
    user_message = f"""Email to classify:
From: {sender}
Subject: {subject}
Preview: {preview}
Is Reply: {is_reply}
Has Attachment: {has_attachment}

{task_prompt}

Response (ONLY the category name): """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=50,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
    
    # Parse response
    response_text = response.choices[0].message.content.strip().lower()
    
    # Extract category
    for category in EmailCategory:
        if category.value.lower() in response_text.lower():
            return category
    
    # Default to informational if unclear
    return EmailCategory.INFORMATIONAL


def run_baseline(task_id: str = "task_1_easy", verbose: bool = True) -> Dict[str, Any]:
    """
    Run baseline inference on a task.
    
    Args:
        task_id: Task to run (task_1_easy, task_2_medium, task_3_hard)
        verbose: Print detailed output
    
    Returns:
        Performance metrics and scores
    """
    
    # Initialize
    api_key = load_api_key()
    client = OpenAI(api_key=api_key)
    
    env = EmailTriageEnv(task_id=task_id)
    observation = env.reset()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Running Baseline on {task_id}")
        print(f"{'='*60}")
        print(f"Task: {env.task.description}")
        print(f"Difficulty: {env.task.difficulty}")
        print(f"Total emails: {observation.total_count}\n")
    
    done = False
    step = 0
    results = []
    
    while not done:
        step += 1
        current_email = observation.current_email
        
        try:
            # Get classification from GPT
            predicted_category = classify_email_with_gpt(
                client=client,
                sender=current_email.sender,
                subject=current_email.subject,
                preview=current_email.preview,
                is_reply=current_email.is_reply,
                has_attachment=current_email.has_attachment,
                task_id=task_id,
            )
            
            # Take action
            action = Action(
                action_type=ActionType.CLASSIFY,
                category=predicted_category,
                reason="GPT classification"
            )
            
            observation, reward, done, info = env.step(action)
            
            # Record result
            is_correct = current_email.ground_truth_category == predicted_category
            results.append({
                "step": step,
                "email_id": current_email.id,
                "predicted": predicted_category,
                "ground_truth": current_email.ground_truth_category,
                "correct": is_correct,
                "reward": reward.step_reward,
            })
            
            if verbose:
                status = "✓" if is_correct else "✗"
                print(
                    f"{status} Step {step}: {current_email.subject[:50]:50s} "
                    f"→ {predicted_category:12s} (acc: {reward.accuracy:.2%})"
                )
        
        except Exception as e:
            print(f"Error processing email {current_email.id}: {e}")
            done = True
            break
    
    # Calculate final metrics
    state = env.state()
    final_grade = env.task.grade()
    accuracy = state.total_correct / (state.total_correct + state.total_wrong) \
        if (state.total_correct + state.total_wrong) > 0 else 0.0
    
    metrics = {
        "task_id": task_id,
        "difficulty": env.task.difficulty,
        "total_emails": state.total_correct + state.total_wrong,
        "correct": state.total_correct,
        "wrong": state.total_wrong,
        "accuracy": accuracy,
        "final_grade": final_grade,
        "results": results,
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Results for {task_id}")
        print(f"{'='*60}")
        print(f"Accuracy: {accuracy:.2%} ({state.total_correct}/{state.total_correct + state.total_wrong})")
        print(f"Final Grade: {final_grade:.2f}/1.0")
        print(f"{'='*60}\n")
    
    return metrics


def main():
    """Run baseline on all tasks."""
    
    print("Email Triage Baseline Inference")
    print("================================\n")
    
    all_results = {}
    
    for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
        try:
            metrics = run_baseline(task_id=task_id, verbose=True)
            all_results[task_id] = metrics
        except Exception as e:
            print(f"Failed to run {task_id}: {e}\n")
            all_results[task_id] = {"error": str(e)}
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    total_grade = 0.0
    count = 0
    
    for task_id, metrics in all_results.items():
        if "error" not in metrics:
            grade = metrics.get("final_grade", 0.0)
            accuracy = metrics.get("accuracy", 0.0)
            print(
                f"{task_id:15s}: Accuracy {accuracy:6.2%} | "
                f"Grade {grade:5.2f}/1.0"
            )
            total_grade += grade
            count += 1
    
    if count > 0:
        avg_grade = total_grade / count
        print("-" * 60)
        print(f"Average Grade: {avg_grade:.2f}/1.0")
    
    print("="*60 + "\n")
    
    # Save results
    with open("baseline_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("✓ Results saved to baseline_results.json")
    
    return all_results


if __name__ == "__main__":
    main()
