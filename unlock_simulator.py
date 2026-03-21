import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from user_store.user_hub import load_profile, save_profile

def unlock_simulator(user_id="default_user"):
    profile = load_profile(user_id)
    
    # Ensure they have completed at least 5 levels to unlock the simulator
    completed = set(profile.get("levels_completed", []))
    for i in range(1, 6):
        completed.add(i)
        
    profile["levels"] = list(completed)
    profile["levels_completed"] = list(completed)
    profile["current_level"] = max(6, profile.get("current_level", 6))
    profile["initial_exam_completed"] = True
    
    save_profile(user_id, profile)
    print(f"Unlocked levels 1-5 for {user_id}. Simulator should now be visible on refresh.")

if __name__ == "__main__":
    unlock_simulator("Surya")
    unlock_simulator("surya")
    unlock_simulator("admin")
