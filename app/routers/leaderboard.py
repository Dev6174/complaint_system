# pyrefly: ignore [missing-import]
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])

@router.get("")
def get_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns top 50 users by points, with badges unserialized.
    """
    top_users = db.query(User).order_by(User.points.desc()).limit(50).all()
    
    leaderboard = []
    for user in top_users:
        try:
            badges_list = json.loads(user.badges)
        except Exception:
            badges_list = []
            
        leaderboard.append({
            "name": user.name,
            "points": user.points,
            "badges": badges_list,
            "role": user.role
        })
        
    return leaderboard
