"""
eval/run_all.py - Master evaluation runner for Arivaran.
Runs the complete test and measurement suite in order:
1. run_eval.py       -> Evaluates messages.csv on dev & test splits
2. run_robustness.py -> Runs evasion, offline fake server, and link safety tests
3. run_latency.py    -> Measures 20-run median & p95 latencies and specs
4. check_privacy.py  -> Verifies zero PII leakage in storage and logs

Generates the unified report at eval/results.md.
"""

import os
import sys
import subprocess

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON_EXE = sys.executable


def run_step(script_name: str, description: str):
    script_path = os.path.join(WORKSPACE_ROOT, "eval", script_name)
    print("=" * 70)
    print(f"STEP: {description} ({script_name})")
    print("=" * 70)
    result = subprocess.run([PYTHON_EXE, script_path], cwd=WORKSPACE_ROOT)
    if result.returncode != 0:
        print(f"ERROR: {script_name} exited with code {result.returncode}", file=sys.stderr)
        # Continue executing other steps so all reports are generated honestly
    print()


def main():
    print("======================================================================")
    print("ARIVARAN EVALUATION & BENCHMARK HARNESS RUNNER")
    print("======================================================================")
    print(f"Python interpreter: {PYTHON_EXE}")
    print(f"Workspace root:     {WORKSPACE_ROOT}\n")

    # Step 1: Run accuracy eval and create results.md
    run_step("run_eval.py", "Benchmark Accuracy & Multi-Class Confusion Matrix")

    # Step 2: Run robustness and link evasion suite
    run_step("run_robustness.py", "Robustness & Security Edge Cases (R01-R15)")

    # Step 3: Run latency benchmark
    run_step("run_latency.py", "Latency Benchmarking (20 Runs Median & p95)")

    # Step 4: Run privacy and PII leakage audit
    run_step("check_privacy.py", "Privacy & PII Leakage Storage Audit")

    # Step 5: Skipped per user instruction (Do NOT run eval/run_blind.py; blind run is frozen)
    print("SKIPPING: run_blind.py per evaluation protocol rules (blind dataset run is frozen).")

    results_path = os.path.join(WORKSPACE_ROOT, "eval", "results.md")
    print("======================================================================")
    print(f"ALL EVALUATION SUITES COMPLETE! Unified report: {results_path}")
    print("======================================================================")


if __name__ == "__main__":
    main()
