from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_agents_status():
    # Starter implementation
    return {
        "supervisor": "idle",
        "inventory": "active",
        "procurement": "idle",
        "finance": "idle",
        "logistics": "idle"
    }
