#!/usr/bin/env python3
"""
CLI entry point for the data processing pipeline.

Usage:
    python main.py --config config.yaml
    python main.py --config config.yaml --input data/input/other.csv --output data/output/other.csv
    python main.py --config config.yaml --source-type json --input data/input/users_sample.json
"""

from __future__ import annotations

import argparse
import sys

from src.exceptions import PipelineError
from src.pipeline import Pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the data processing pipeline.")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file.")
    parser.add_argument("--input", dest="input_path", default=None, help="Override source.path.")
    parser.add_argument("--output", dest="output_path", default=None, help="Override output.path.")
    parser.add_argument(
        "--source-type",
        dest="source_type",
        default=None,
        choices=["csv", "json", "api"],
        help="Override source.type.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overrides = {
        "input_path": args.input_path,
        "output_path": args.output_path,
        "source_type": args.source_type,
    }

    try:
        pipeline = Pipeline(config_path=args.config, overrides=overrides)
        stats = pipeline.run()
    except PipelineError as e:
        print(f"Pipeline failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    print("\nPipeline run summary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
