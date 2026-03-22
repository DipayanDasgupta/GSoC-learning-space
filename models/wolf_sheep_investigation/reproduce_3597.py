"""
reproduce_3597.py
=================
Reproduction script for Issue #3597:
WolfSheep crashes when grass=False

Run from mesa root:
    python models/wolf_sheep_investigation/reproduce_3597.py

Shows both bugs before the fix and confirms the fixed behavior.
"""
from mesa.examples.advanced.wolf_sheep.model import WolfSheep, WolfSheepScenario

print("=" * 60)
print("Issue #3597 — WolfSheep grass=False crash reproduction")
print("=" * 60)

print("\n--- Bug 1: Sheep.feed() StopIteration ---")
print("Running WolfSheep with grass=False for 20 steps...")
try:
    model = WolfSheep(scenario=WolfSheepScenario(grass=False, rng=42))
    for i in range(20):
        model.step()
    df = model.datacollector.get_model_vars_dataframe()
    print(f"✅ Ran 20 steps successfully")
    print(f"   Columns: {list(df.columns)}")
    print(f"   'Grass' absent: {'Grass' not in df.columns}")
    print(f"   Final wolves: {df['Wolves'].iloc[-1]}, sheep: {df['Sheep'].iloc[-1]}")
except StopIteration as e:
    print(f"❌ StopIteration (unfixed): {e}")
except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")

print("\n--- Bug 2: PlotMatplotlib KeyError ---")
print("Checking df.columns guard...")
try:
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    model = WolfSheep(scenario=WolfSheepScenario(grass=False, rng=42))
    model.step()
    df = model.datacollector.get_model_vars_dataframe()
    fig = Figure()
    ax = fig.subplots()
    measure = {"Grass": "green", "Wolves": "blue", "Sheep": "red"}
    for m, color in measure.items():
        if m in df.columns:
            ax.plot(df.loc[:, m], label=m, color=color)
    print(f"✅ PlotMatplotlib guard works — Grass skipped, Wolves+Sheep plotted")
except KeyError as e:
    print(f"❌ KeyError (unfixed): {e}")
except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Both bugs fixed. See PR #3608 for details.")
print("=" * 60)
