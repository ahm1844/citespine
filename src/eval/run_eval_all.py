#!/usr/bin/env python3
"""
Main evaluation runner - orchestrates all evaluation components.

Runs the complete evaluation suite and generates comprehensive reports.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_command(cmd, description):
    """Run a command and capture output."""
    print(f"Running {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        print(f"✓ {description} completed")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e.stderr}")
        return False, e.stderr

def main():
    parser = argparse.ArgumentParser(description="Run complete evaluation suite")
    parser.add_argument("--reports-dir", default="data/eval",
                       help="Output directory for evaluation reports")
    parser.add_argument("--skip", nargs="+", 
                       choices=["faithfulness", "filters", "asof", "negatives", "structured", "perf", "replay", "pii"],
                       help="Skip specific evaluation components")
    parser.add_argument("--parallel", action="store_true",
                       help="Run evaluations in parallel where possible")
    
    args = parser.parse_args()
    
    # Ensure reports directory exists
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Define evaluation components
    components = [
        ("faithfulness", "make eval_faithfulness"),
        ("filters", "make eval_filters"), 
        ("asof", "make eval_asof"),
        ("negatives", "make eval_negatives"),
        ("structured", "make eval_structured"),
        ("perf", "make eval_perf"),
        ("replay", "make eval_replay"),
        ("pii", "make eval_pii")
    ]
    
    # Filter out skipped components
    if args.skip:
        components = [(name, cmd) for name, cmd in components if name not in args.skip]
    
    print(f"Starting evaluation suite with {len(components)} components...")
    print(f"Reports will be written to: {reports_dir}")
    
    # Run components
    results = {}
    start_time = datetime.utcnow()
    
    if args.parallel:
        # TODO: Implement parallel execution using concurrent.futures
        print("Parallel execution not yet implemented, running sequentially...")
    
    # Sequential execution
    for component_name, command in components:
        success, output = run_command(command, f"{component_name} evaluation")
        results[component_name] = {
            "success": success,
            "output": output[:500] if output else "",  # Truncate long output
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    # Run acceptance gates check
    print("\nRunning acceptance gates validation...")
    gates_success, gates_output = run_command(
        "make gates", 
        "acceptance gates validation"
    )
    
    # Generate overall summary
    successful = sum(1 for r in results.values() if r["success"])
    total = len(components)
    
    summary = {
        "status": "COMPLETED" if gates_success else "FAILED",
        "components_run": total,
        "components_passed": successful,
        "components_failed": total - successful,
        "gates_passed": gates_success,
        "start_time": start_time.isoformat() + "Z",
        "end_time": datetime.utcnow().isoformat() + "Z",
        "results": results,
        "gates_output": gates_output[:500] if gates_output else "",
        "metadata": {
            "runner_version": "v1.0.0",
            "reports_dir": str(reports_dir),
            "skipped_components": args.skip or []
        }
    }
    
    # Write summary report
    summary_file = reports_dir / "evaluation_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print final results
    print(f"\n{'='*60}")
    print(f"EVALUATION SUITE SUMMARY")
    print(f"{'='*60}")
    print(f"Components: {successful}/{total} passed")
    print(f"Acceptance Gates: {'PASSED' if gates_success else 'FAILED'}")
    print(f"Overall Status: {summary['status']}")
    print(f"Summary Report: {summary_file}")
    print(f"{'='*60}")
    
    if not gates_success or successful < total:
        print("❌ Evaluation suite failed - check individual reports for details")
        sys.exit(1)
    else:
        print("✅ All evaluations passed")
        sys.exit(0)

if __name__ == "__main__":
    main()
