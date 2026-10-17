"""CLI: ``python -m app run "Photosynthesis"`` executes a pipeline synchronously."""

import argparse
import logging

from app.config import get_settings
from app.models import RunRequest
from app.pipeline import create_run, execute
from app.state import RunStore


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run the pipeline for a topic")
    run.add_argument("topic")
    run.add_argument("--audience", default="high school students")
    run.add_argument("--minutes", type=float, default=3.0)
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")
    store = RunStore(settings.runs_dir)
    request = RunRequest(topic=args.topic, audience=args.audience, duration_minutes=args.minutes)
    state = execute(store, settings, create_run(store, settings, request).id)

    print(f"run {state.id}: {state.status}")
    if state.output_path:
        print(f"output: {state.output_path}")
    return 0 if state.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
