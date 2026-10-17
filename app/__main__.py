"""CLI for running the pipeline without the API.

python -m app run --title "What is RAG?" --idea "rough notes..." --stages script=stub voice=stub
python -m app approve <run_id> --all
"""

import argparse
import logging

from app.config import get_settings
from app.models import RunConfig, StageChoice
from app.pipeline import approve, create_run, execute
from app.stages import CHECKLIST
from app.state import RunStore


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Create a run and execute it up to the review gate")
    run.add_argument("--title", required=True)
    run.add_argument("--idea", required=True)
    run.add_argument("--stages", nargs="*", default=[], metavar="STAGE=PROVIDER")

    ok = sub.add_parser("approve", help="Approve a run at the review gate and finish it")
    ok.add_argument("run_id")
    ok.add_argument("--all", action="store_true", required=True, help="Tick every checklist item")

    args = parser.parse_args()
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")
    store = RunStore(settings.runs_dir)

    if args.command == "run":
        choices = [
            StageChoice(stage=s, provider=p) for s, p in (a.split("=", 1) for a in args.stages)
        ]
        config = RunConfig(title=args.title, idea=args.idea, stages=choices)
        run_id = create_run(store, config).id
    else:
        run_id = approve(store, args.run_id, dict.fromkeys(CHECKLIST, True)).id

    state = execute(store, settings, run_id)
    print(f"run {state.id}: {state.status}")
    for stage in state.stages:
        print(f"  {stage.stage:<11} {stage.status:<16} {stage.provider or ''}")
    return 1 if state.status == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
