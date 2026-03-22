"""
app_grass_false_demo.py
=======================
Demonstration of Issue #3597 fix — WolfSheep running with grass=False.

This app shows the fixed model running correctly with grass disabled.
The key fix: lineplot_component only includes metrics that exist in
the datacollector for the current configuration.

Run with:
    solara run models/wolf_sheep_investigation/app_grass_false_demo.py

Or from mesa root:
    cd ~/mesa && solara run ~/GSoC-learning-space/models/wolf_sheep_investigation/app_grass_false_demo.py
"""

import solara
from mesa.examples.advanced.wolf_sheep.agents import GrassPatch, Sheep, Wolf
from mesa.examples.advanced.wolf_sheep.model import WolfSheep, WolfSheepScenario
from mesa.visualization import (
    CommandConsole,
    Slider,
    SolaraViz,
    SpaceRenderer,
    make_plot_component,
)
from mesa.visualization.components import AgentPortrayalStyle


def wolf_sheep_portrayal(agent):
    """Portray agents — GrassPatch hidden when grass=False (none exist)."""
    if agent is None:
        return

    portrayal = AgentPortrayalStyle(size=50, marker="o", zorder=2)

    if isinstance(agent, Wolf):
        portrayal.update(("color", "#ff4444"))
    elif isinstance(agent, Sheep):
        portrayal.update(("color", "#74b9ff"))
    elif isinstance(agent, GrassPatch):
        if agent.fully_grown:
            portrayal.update(("color", "tab:green"))
        else:
            portrayal.update(("color", "tab:brown"))
        portrayal.update(("marker", "s"), ("size", 125), ("zorder", 1))

    return portrayal


model_params = {
    "rng": {
        "type": "InputText",
        "value": 42,
        "label": "Random Seed",
    },
    "grass": {
        "type": "Select",
        "value": False,          # default to False to demo the fix
        "values": [True, False],
        "label": "grass regrowth enabled?",
    },
    "grass_regrowth_time": Slider("Grass Regrowth Time", 20, 1, 50),
    "initial_sheep": Slider("Initial Sheep Population", 100, 10, 300),
    "sheep_reproduce": Slider("Sheep Reproduction Rate", 0.04, 0.01, 1.0, 0.01),
    "initial_wolves": Slider("Initial Wolf Population", 10, 5, 100),
    "wolf_reproduce": Slider("Wolf Reproduction Rate", 0.05, 0.01, 1.0, 0.01),
    "wolf_gain_from_food": Slider("Wolf Gain From Food Rate", 20, 1, 50),
    "sheep_gain_from_food": Slider("Sheep Gain From Food", 4, 1, 10),
}


def post_process_space(ax):
    """Clean up space axes."""
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def post_process_lines(ax):
    """Legend outside plot area."""
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.9))


# FIX: only plot Wolves and Sheep — Grass is absent when grass=False
# The original app.py always included "Grass" which caused KeyError
lineplot_component = make_plot_component(
    {"Wolves": "tab:orange", "Sheep": "tab:cyan"},
    post_process=post_process_lines,
)

model = WolfSheep(scenario=WolfSheepScenario(grass=False))

renderer = SpaceRenderer(
    model,
    backend="matplotlib",
).setup_agents(wolf_sheep_portrayal)
renderer.post_process = post_process_space
renderer.draw_agents()

page = SolaraViz(
    model,
    renderer,
    components=[lineplot_component, CommandConsole],
    model_params=model_params,
    name="Wolf Sheep — grass=False Fix Demo (#3597)",
)
page  # noqa
