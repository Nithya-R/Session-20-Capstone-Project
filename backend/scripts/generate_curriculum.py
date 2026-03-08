import asyncio
import sys
import argparse
from pathlib import Path

# Add backend to path for imports
ROOT = Path(__file__).parent.parent.resolve()
sys.path.append(str(ROOT))

from services.curriculum_service import curriculum_service

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-run", action="store_true", help="Only process Level 1")
    parser.add_argument("--level", type=int, help="Process a specific level")
    args = parser.parse_args()
    
    if args.level:
        await curriculum_service.generate_level(args.level)
    elif args.test_run:
        await curriculum_service.generate_level(1)
    else:
        for i in range(1, 21):
            success = await curriculum_service.generate_level(i)
            if not success:
                print(f"Skipping further generation as Level {i} data may not exist.")

if __name__ == "__main__":
    asyncio.run(main())
