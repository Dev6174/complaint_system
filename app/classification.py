# pyrefly: ignore [missing-import]
import httpx
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from app.config import settings

logger = logging.getLogger("complaint_system.classification")

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN
        self.last_state_change = datetime.now(timezone.utc)

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        logger.warning(f"Circuit breaker failure registered: {self.failure_count}/{self.failure_threshold}")
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = datetime.now(timezone.utc)
            logger.error(f"Circuit breaker tripped to OPEN state. Fallback active.")

    def allow_request(self) -> bool:
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            elapsed = (datetime.now(timezone.utc) - self.last_state_change).total_seconds()
            if elapsed > self.recovery_timeout_seconds:
                logger.info("Circuit breaker entering HALF-OPEN state (allowing test request)")
                # Let request pass, state stays OPEN until success or failure
                return True
            return False
        return True

# Instantiate global circuit breaker
classification_breaker = CircuitBreaker()

def classify_issue_local(title: str, description: str) -> Dict[str, Any]:
    """
    Built-in rule/keyword-based fallback classifier.
    Never blocks submission, degrades gracefully.
    """
    text = (title + " " + description).lower()
    
    # Priority defaults
    category = "Other"
    priority = "Medium"
    reasoning = "Local rule-based classifier fallback used."
    confidence = 0.65

    # Categories from requirements
    rules = [
        (["pothole", "cracks", "pavement", "street repair", "bump", "potholes"], "Potholes", "Medium"),
        (["leak", "water", "pipe", "flooding", "burst", "drain", "leakage"], "Water Leakage", "Medium"),
        (["streetlight", "lamp", "dark", "bulb", "street light", "blackout", "streetlights"], "Damaged Streetlights", "Low"),
        (["waste", "garbage", "trash", "litter", "dump", "smell", "bin", "refuse"], "Waste Management", "Low"),
        (["danger", "hazard", "safety", "exposed wire", "fire", "security", "collapse", "wire"], "Public Safety Hazards", "High"),
        (["bridge", "sidewalk", "bench", "park", "infrastructure", "construction", "sign"], "Infrastructure Problems", "Medium")
    ]

    for keywords, cat, prio in rules:
        if any(keyword in text for keyword in keywords):
            category = cat
            priority = prio
            reasoning = f"Local keyword match found for '{category}' category."
            confidence = 0.85
            break

    return {
        "category": category,
        "priority": priority,
        "confidence": confidence,
        "reasoning": reasoning
    }

async def suggest_category_and_priority(title: str, description: str, has_attachment: bool = False) -> Dict[str, Any]:
    """
    Categorizes the issue using the configured automated categorization service.
    If unavailable or timed out, falls back to the local keyword classifier.
    """
    if not classification_breaker.allow_request() or not settings.AI_CLASSIFIER_API_KEY:
        logger.info("Using local fallback classifier (circuit breaker open or API key missing)")
        return classify_issue_local(title, description)

    try:
        # API payloads & headers
        payload = {
            "title": title,
            "description": description,
            "has_attachment": has_attachment
        }
        headers = {
            "Authorization": f"Bearer {settings.AI_CLASSIFIER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 3 second timeout as per security/load handling
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(
                settings.AI_CLASSIFIER_ENDPOINT,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                classification_breaker.record_success()
                return {
                    "category": data.get("category", "Other"),
                    "priority": data.get("priority", "Medium"),
                    "confidence": float(data.get("confidence", 0.90)),
                    "reasoning": data.get("reasoning", "Categorized by automated service.")
                }
            else:
                logger.warning(f"External classification API returned status {response.status_code}")
                classification_breaker.record_failure()
    except Exception as e:
        logger.error(f"External classification request failed: {str(e)}")
        classification_breaker.record_failure()

    # Fallback in case of failure
    return classify_issue_local(title, description)
