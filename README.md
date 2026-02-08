# Capital (MVP Simulation Core)

This repository contains a headless simulation core for **Capital**, a minimal closed-loop economy sim. It is intentionally data-driven and modular to support expansion.

## Run

```bash
python main.py --ticks 200 --seed 42
```

## Visual Mode

```bash
python main.py --visual --width 20 --height 20 --tick-ms 200
```

Close the window to stop the simulation.

## Data

* `data/goods.json` defines goods and base utility.
* `data/recipes.json` defines production recipes.

## Notes

The simulation is intentionally small and deterministic when seeded, suitable for balancing before adding a UI.
