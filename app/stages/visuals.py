"""Stage 4 — visuals: produce one image per scene."""

from typing import Any
from xml.sax.saxutils import escape

from app.stages.base import Provider, ProviderRegistry, StageContext

registry = ProviderRegistry("visuals")

_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">
  <rect width="100%" height="100%" fill="#0f172a"/>
  <text x="50%" y="45%" fill="#f8fafc" font-family="sans-serif" font-size="96"
        text-anchor="middle">{heading}</text>
  <text x="50%" y="58%" fill="#94a3b8" font-family="sans-serif" font-size="48"
        text-anchor="middle">{topic}</text>
</svg>
"""


@registry.register("mock")
class MockVisualsProvider(Provider):
    """Renders a placeholder title-card SVG per scene."""

    def run(self, ctx: StageContext) -> dict[str, Any]:
        out_dir = ctx.run_dir / "visuals"
        out_dir.mkdir(exist_ok=True)
        images = []
        for scene in ctx.artifacts["storyboard"]["scenes"]:
            path = out_dir / f"scene_{scene['index']:02d}.svg"
            svg = _SVG.format(heading=escape(scene["heading"]), topic=escape(ctx.request.topic))
            path.write_text(svg, encoding="utf-8")
            images.append({"scene": scene["index"], "path": str(path)})
        return {"images": images}
