# SpaceRenderer Migration Model

## What this model does

A minimal Schelling Segregation model with Solara visualisation that uses the
**new `SpaceRenderer.render()` API** exclusively — demonstrating the migration
pattern from PR #3283.

Before PR #3283, core examples called the deprecated `draw_agents()` and
`draw_propertylayer()` methods separately, generating `FutureWarning` noise.
The new API folds the full draw pipeline into a single `renderer.render()` call.

## Output

Running `solara run models/spacerenderer_migration/app.py` shows a Schelling
segregation grid with zero `FutureWarning` output in the console.

## Mesa features used

- `SpaceRenderer` (new unified API, PR #3283)
- `OrthogonalMooreGrid`, `CellAgent`, `PropertyLayer`
- `SolaraViz`, `Slider`, `make_plot_component`

## Connection to PR #3283

While reading the CI warnings in the core examples, I noticed `draw_agents()`
appearing in four files after the tutorials had been migrated. PR #3283
completes that migration for `wolf_sheep/app.py`, `epstein_civil_violence/app.py`,
`sugarscape_g1mt/app.py`, and `conways_game_of_life/app.py`. This model
demonstrates the correct pattern in isolation.
