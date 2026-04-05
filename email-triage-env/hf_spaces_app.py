"""HuggingFace Spaces configuration for email-triage-env."""

import os
import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory


def run_inference_hf_spaces():
    """
    Main entry point for HF Spaces.
    Runs baseline inference and displays results.
    """
    
    print("="*70)
    print("Email Triage Environment - HuggingFace Spaces Demo")
    print("="*70)
    
    all_results = {}
    
    for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
        print(f"\n{'─'*70}")
        print(f"Running {task_id.upper()}")
        print(f"{'─'*70}\n")
        
        env = EmailTriageEnv(task_id=task_id)
        observation = env.reset()
        
        print(f"Task: {env.task.description}")
        print(f"Difficulty: {env.task.difficulty.upper()}")
        print(f"Total emails: {observation.total_count}\n")
        
        done = False
        step = 0
        results = []
        
        while not done:
            step += 1
            current_email = observation.current_email
            
            # Simple heuristic classifier (not LLM, since HF Spaces may not have API key)
            predicted_category = simple_classify(
                subject=current_email.subject,
                preview=current_email.preview,
                sender=current_email.sender,
                task_id=task_id
            )
            
            action = Action(
                action_type=ActionType.CLASSIFY,
                category=predicted_category,
                reason="Heuristic classification"
            )
            
            observation, reward, done, info = env.step(action)
            
            is_correct = current_email.ground_truth_category == predicted_category
            results.append({
                "step": step,
                "email": current_email.subject[:50],
                "predicted": predicted_category.value,
                "ground_truth": current_email.ground_truth_category.value,
                "correct": is_correct,
            })
            
            status = "✓" if is_correct else "✗"
            print(
                f"{status} {step:2d}. {current_email.subject[:50]:50s} "
                f"→ {predicted_category.value:12s} (acc: {reward.accuracy:.1%})"
            )
        
        state = env.state()
        final_grade = env.task.grade()
        accuracy = state.total_correct / (state.total_correct + state.total_wrong) \
            if (state.total_correct + state.total_wrong) > 0 else 0.0
        
        all_results[task_id] = {
            "accuracy": accuracy,
            "grade": final_grade,
            "correct": state.total_correct,
            "total": state.total_correct + state.total_wrong,
        }
        
        print(f"\nAccuracy: {accuracy:.1%} ({state.total_correct}/{state.total_correct + state.total_wrong})")
        print(f"Final Grade: {final_grade:.2f}/1.0")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    total_grade = 0.0
    for task_id, metrics in all_results.items():
        grade = metrics["grade"]
        accuracy = metrics["accuracy"]
        print(
            f"{task_id:15s}: Accuracy {accuracy:6.1%} | Grade {grade:5.2f}/1.0"
        )
        total_grade += grade
    
    avg_grade = total_grade / len(all_results)
    print("-"*70)
    print(f"Average Grade: {avg_grade:.2f}/1.0")
    print("="*70)
    
    return all_results


def simple_classify(subject: str, preview: str, sender: str, task_id: str) -> EmailCategory:
    """
    Simple heuristic classifier (no API required).
    Used for HF Spaces demo when OPENAI_API_KEY not available.
    """
    
    text = (subject + " " + preview + " " + sender).lower()
    
    # Spam detection
    if any(word in text for word in ["viagra", "click here", "claim prize", "verify account", "urgent:", "!!!", "free money"]):
        if any(word in sender.lower() for word in ["suspicious", "temp", "crypto"]):
            return EmailCategory.SPAM
    
    # Urgent
    if any(word in text for word in [
        "critical", "urgent", "alert", "emergency", "production", "down", "outage",
        "security", "leak", "breach", "asap", "immediate", "immediately"
    ]):
        return EmailCategory.URGENT
    
    # Follow-up
    if subject.lower().startswith("re:") or any(word in text for word in [
        "awaiting", "waiting for", "please confirm", "need your input", "decision",
        "approval needed", "action needed"
    ]):
        return EmailCategory.FOLLOW_UP
    
    # Default to informational
    return EmailCategory.INFORMATIONAL


if __name__ == "__main__":
    run_inference_hf_spaces()
