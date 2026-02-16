#!/usr/bin/env python3
"""Manual test to demonstrate interrupt handling.

Run this script and press Ctrl+C to test:
- First Ctrl+C: Shows message and sets flag
- Second Ctrl+C: Immediately exits

Usage:
    python tests/manual/test_interrupt_demo.py
"""

import time
from saha.orchestrator.loop import InterruptHandler


def simulate_long_running_task():
    """Simulate a long-running task with phase checks."""
    print("Starting simulated agentic loop...")
    print("Press Ctrl+C to test interrupt handling\n")

    phases = [
        "Implementation",
        "Test Critique",
        "QA Verification",
        "Code Quality",
        "Manager Update",
        "DoD Check",
    ]

    with InterruptHandler() as handler:
        try:
            for iteration in range(1, 4):
                print(f"\n{'='*60}")
                print(f"Iteration {iteration}/3")
                print(f"{'='*60}")

                for phase in phases:
                    # Check for interrupt before starting phase
                    if handler.was_interrupted():
                        print(f"\n✓ Interrupt detected before {phase}")
                        raise KeyboardInterrupt

                    print(f"\n▶ Running {phase}...", end="", flush=True)

                    # Simulate phase work
                    for i in range(5):
                        time.sleep(0.5)
                        print(".", end="", flush=True)

                    print(" ✓")

                    # Check for interrupt after phase
                    if handler.was_interrupted():
                        print(f"\n✓ Interrupt detected after {phase}")
                        raise KeyboardInterrupt

        except KeyboardInterrupt:
            print("\n\n{'='*60}")
            print("INTERRUPT HANDLING")
            print(f"{'='*60}")
            print(f"Interrupt count: {handler.interrupt_count}")
            print("Running cleanup...")
            time.sleep(1)
            print("✓ Cleanup complete")
            return

    print("\n\n{'='*60}")
    print("COMPLETED")
    print(f"{'='*60}")
    print("All iterations finished successfully!")


if __name__ == "__main__":
    simulate_long_running_task()
