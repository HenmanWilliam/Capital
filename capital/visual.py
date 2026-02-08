from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .sim import Simulation, SimulationConfig


TILE_COLORS: Dict[str, str] = {
    "Forest": "#2e7d32",
    "Ore": "#6d4c41",
    "FertileLand": "#9ccc65",
    "River": "#42a5f5",
    "Empty": "#cfd8dc",
}

BUILDING_COLORS: Dict[str, str] = {
    "forestry": "#1b5e20",
    "farming": "#f9a825",
    "waterworks": "#0277bd",
    "mining": "#424242",
}


@dataclass
class VisualConfig:
    tick_ms: int = 200
    tile_size: int = 24


class VisualSimulation:
    def __init__(self, simulation: Simulation, config: VisualConfig) -> None:
        self.simulation = simulation
        self.config = config
        self.root = tk.Tk()
        self.root.title("Capital Simulation")

        self.canvas = tk.Canvas(
            self.root,
            width=simulation.world.width * config.tile_size,
            height=simulation.world.height * config.tile_size,
            bg="white",
        )
        self.canvas.grid(row=0, column=0, padx=8, pady=8)

        self.info = tk.Text(self.root, width=40, height=20)
        self.info.grid(row=0, column=1, padx=8, pady=8, sticky="n")
        self.info.configure(state="disabled")

        self.tick_count = 0
        self._draw_base_map()

    def _draw_base_map(self) -> None:
        self.canvas.delete("tile")
        size = self.config.tile_size
        for y in range(self.simulation.world.height):
            for x in range(self.simulation.world.width):
                tile = self.simulation.world.tile_at(x, y)
                color = TILE_COLORS.get(tile, "#ffffff")
                self.canvas.create_rectangle(
                    x * size,
                    y * size,
                    (x + 1) * size,
                    (y + 1) * size,
                    fill=color,
                    outline="#90a4ae",
                    tags="tile",
                )

    def _draw_buildings(self) -> None:
        self.canvas.delete("building")
        size = self.config.tile_size
        padding = size * 0.2
        for (x, y), building in self.simulation.world.buildings.items():
            color = BUILDING_COLORS.get(building, "#000000")
            self.canvas.create_rectangle(
                x * size + padding,
                y * size + padding,
                (x + 1) * size - padding,
                (y + 1) * size - padding,
                fill=color,
                outline="#263238",
                tags="building",
            )

    def _update_info(self) -> None:
        building_counts = self.simulation.world.building_counts()
        unemployed = sum(1 for h in self.simulation.households if h.employed_by is None)
        avg_cash = sum(h.cash for h in self.simulation.households) / len(self.simulation.households)
        lines = [
            f"Tick: {self.tick_count}",
            f"Unemployed: {unemployed}",
            f"Avg Cash: {avg_cash:.1f}",
            f"Active Firms: {sum(1 for f in self.simulation.firms if f.active)}",
            "",
            "Prices:",
        ]
        for good, price in self.simulation.market.prices.items():
            lines.append(f"  {good}: {price:.2f}")
        lines.append("")
        lines.append("Buildings:")
        for building, count in building_counts.items():
            lines.append(f"  {building}: {count}")

        self.info.configure(state="normal")
        self.info.delete("1.0", tk.END)
        self.info.insert(tk.END, "\n".join(lines))
        self.info.configure(state="disabled")

    def _step(self) -> None:
        self.tick_count += 1
        self.simulation.tick(self.tick_count)
        if self.tick_count % 2 == 0:
            self._draw_buildings()
            self._update_info()
        self.root.after(self.config.tick_ms, self._step)

    def run(self) -> None:
        self._update_info()
        self._draw_buildings()
        self.root.after(self.config.tick_ms, self._step)
        self.root.mainloop()


def run_visual_simulation(ticks: int, seed: int, world_width: int, world_height: int, tick_ms: int) -> None:
    config = SimulationConfig(
        ticks=ticks,
        seed=seed,
        households=12,
        workers_per_firm=2,
        world_width=world_width,
        world_height=world_height,
    )
    simulation = Simulation(data_path=Path("data"), config=config)
    visual = VisualSimulation(simulation, VisualConfig(tick_ms=tick_ms))
    visual.run()
