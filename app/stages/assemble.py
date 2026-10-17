"""Stage 5 — assemble: combine audio and visuals into the final deliverable."""

import json
from typing import Any

from app.stages.base import Provider, ProviderRegistry, StageContext

registry = ProviderRegistry("assemble")


@registry.register("mock")
class MockAssembleProvider(Provider):
    """Writes a timeline manifest instead of encoding video (an ffmpeg provider replaces this)."""

    def run(self, ctx: StageContext) -> dict[str, Any]:
        clips = {c["scene"]: c for c in ctx.artifacts["voice"]["clips"]}
        images = {i["scene"]: i for i in ctx.artifacts["visuals"]["images"]}

        timeline, cursor = [], 0.0
        for scene in ctx.artifacts["storyboard"]["scenes"]:
            idx = scene["index"]
            timeline.append(
                {
                    "scene": idx,
                    "start_s": round(cursor, 2),
                    "duration_s": clips[idx]["duration_s"],
                    "audio": clips[idx]["path"],
                    "image": images[idx]["path"],
                }
            )
            cursor += clips[idx]["duration_s"]

        out_dir = ctx.outputs_dir / ctx.run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "manifest.json"
        manifest = {
            "title": ctx.artifacts["script"]["title"],
            "total_s": round(cursor, 2),
            "timeline": timeline,
        }
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {"output_path": str(path), "total_s": manifest["total_s"]}
