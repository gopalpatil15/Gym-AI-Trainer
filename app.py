import argparse
import sys

# Import exercise runners
from exercises.pushup import run as run_pushup
from exercises.standing_cable_press import run as run_press
from exercises.bicep_curl import bicep_curl_run   # bicep_curl runs directly on cap loop
from exercises.squat import run as run_squat


def main():
    parser = argparse.ArgumentParser(description="AI Gym Trainer")
    parser.add_argument(
        "--exercise", "-e",
        choices=["pushup", "press", "curl", "squat"],
        required=True,
        help="Choose exercise: pushup | press | curl | squat"
    )
    parser.add_argument(
        "--src", default="0",
        help="0 for webcam, or path/URL to video file"
    )
    args = parser.parse_args()

    try:
        src = int(args.src)
    except ValueError:
        src = args.src

    if args.exercise == "pushup":
        run_pushup(src)
    elif args.exercise == "press":
        run_press(src)
    elif args.exercise == "curl":
        bicep_curl_run()  # directly executes its loop
    elif args.exercise == "squat":
        run_squat(src)
    else:
        print("Invalid choice. Use -h for help.")
        sys.exit(1)

if __name__ == "__main__":
    main()
