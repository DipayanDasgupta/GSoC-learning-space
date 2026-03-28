"""Solara app using the new SpaceRenderer.render() API (PR #3283 pattern).

Run with:
    solara run models/spacerenderer_migration/app.py
"""
import solara
from mesa.visualization import (
    Slider,
    SolaraViz,
    SpaceRenderer,
    make_plot_component,
)
from mesa.visualization.components import AgentPortrayalStyle
from models.spacerenderer_migration.model import GROUP_A, GROUP_B, SchellingAgent, SchellingModel


def portrayal(agent):
    if not isinstance(agent, SchellingAgent):
        return None
    color = "#4a90d9" if agent.group == GROUP_A else "#e85d4a"
    return AgentPortrayalStyle(color=color, size=60, marker="s", zorder=2)


model_params = {
    "homophily": Slider("Homophily threshold", 0.3, 0.0, 1.0, 0.05),
    "density":   Slider("Density", 0.8, 0.1, 1.0, 0.05),
    "width":     {"type": "InputText", "value": 20, "label": "Width"},
    "height":    {"type": "InputText", "value": 20, "label": "Height"},
}

model = SchellingModel()

# ── New API (PR #3283): single render() call — no FutureWarning ──────────────
renderer = SpaceRenderer(model, backend="matplotlib")
renderer.setup_agents(portrayal)
renderer.render()   # ← this is the pattern being demonstrated
# ─────────────────────────────────────────────────────────────────────────────

happiness_plot = make_plot_component({"Happy": "#2ecc71"})

page = SolaraViz(
    model,
    renderer,
    components=[happiness_plot],
    model_params=model_params,
    name="Schelling — SpaceRenderer.render() demo (PR #3283)",
)
page  # noqa
