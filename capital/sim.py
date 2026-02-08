from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .model import Firm, Household, Inventory, MarketAllocation, MarketOrder, MarketState, Recipe
from .systems import ConsumptionSystem, FirmSystem, LaborSystem, MarketSystem, ProductionSystem
from .world import World


@dataclass
class SimulationConfig:
    ticks: int
    seed: int
    households: int
    workers_per_firm: int
    world_width: int
    world_height: int


class Simulation:
    def __init__(self, data_path: Path, config: SimulationConfig) -> None:
        self.data_path = data_path
        self.config = config
        random.seed(config.seed)

        self.goods = self._load_goods()
        self.recipes = self._load_recipes()
        self.market = MarketState(prices={good: values["base_price"] for good, values in self.goods.items()})

        self.world = World.generate(config.world_width, config.world_height, config.seed)
        self.households: List[Household] = [
            Household(household_id=f"household_{i + 1}", cash=50.0) for i in range(config.households)
        ]
        self.firms: List[Firm] = self._initialize_firms()

        self.needs = {"Food": 1.0, "Water": 1.0}

        self.labor_system = LaborSystem()
        self.production_system = ProductionSystem()
        self.market_system = MarketSystem()
        self.consumption_system = ConsumptionSystem()
        self.firm_system = FirmSystem(base_prices={g: v["base_price"] for g, v in self.goods.items()})
        self.rng = random.Random(config.seed)

    def _load_goods(self) -> Dict[str, Dict[str, float]]:
        with (self.data_path / "goods.json").open() as handle:
            return json.load(handle)

    def _load_recipes(self) -> Dict[str, Recipe]:
        with (self.data_path / "recipes.json").open() as handle:
            raw = json.load(handle)
        return {
            entry["id"]: Recipe(
                recipe_id=entry["id"],
                inputs=entry.get("inputs", {}),
                outputs=entry.get("outputs", {}),
                labor_required=entry.get("labor_required", 1),
            )
            for entry in raw
        }

    def _initialize_firms(self) -> List[Firm]:
        firms = []
        for idx, recipe in enumerate(self.recipes.values()):
            firms.append(
                Firm(
                    firm_id=f"firm_{idx + 1}",
                    cash=100.0,
                    recipe=recipe,
                    wage=5.0,
                    workers_needed=self.config.workers_per_firm,
                    inventory=Inventory(),
                )
            )
        return firms

    def _create_orders(self) -> List[MarketOrder]:
        orders: List[MarketOrder] = []
        orders.extend(self.consumption_system.create_orders(self.households, self.needs))
        for firm in self.firms:
            if not firm.active:
                continue
            for good, qty in firm.recipe.inputs.items():
                target = qty * 2
                current = firm.inventory.get(good)
                if current < target:
                    orders.append(
                        MarketOrder(
                            agent_id=firm.firm_id,
                            good=good,
                            quantity=target - current,
                            is_buy=True,
                        )
                    )
            for good, qty in firm.inventory.goods.items():
                if qty > 0:
                    orders.append(
                        MarketOrder(
                            agent_id=firm.firm_id,
                            good=good,
                            quantity=qty,
                            is_buy=False,
                        )
                    )
        return orders

    def _apply_allocations(self, allocations: List[MarketAllocation]) -> None:
        household_lookup = {h.household_id: h for h in self.households}
        firm_lookup = {f.firm_id: f for f in self.firms}
        for allocation in allocations:
            if allocation.is_buy:
                if allocation.agent_id in household_lookup:
                    household = household_lookup[allocation.agent_id]
                    if household.cash >= allocation.total_price:
                        household.cash -= allocation.total_price
                        household.inventory.add(allocation.good, allocation.quantity)
                elif allocation.agent_id in firm_lookup:
                    firm = firm_lookup[allocation.agent_id]
                    if firm.cash >= allocation.total_price:
                        firm.cash -= allocation.total_price
                        firm.inventory.add(allocation.good, allocation.quantity)
            else:
                if allocation.agent_id in firm_lookup:
                    firm = firm_lookup[allocation.agent_id]
                    firm.cash += allocation.total_price
                    firm.inventory.remove(allocation.good, allocation.quantity)

    def _pay_wages(self) -> None:
        household_lookup = {h.household_id: h for h in self.households}
        for firm in self.firms:
            if not firm.active:
                continue
            for worker_id in firm.workers:
                household = household_lookup.get(worker_id)
                if household:
                    household.cash += firm.wage

    def tick(self, step: int) -> None:
        self.labor_system.match(self.households, self.firms)
        self.labor_system.adjust_wages(self.firms)

        self.production_system.produce(self.firms)

        orders = self._create_orders()
        self.market_system.update_prices(self.market, orders)
        allocations = self.market_system.clear_market(self.market, orders)
        self._apply_allocations(allocations)

        self._pay_wages()
        self.consumption_system.consume(self.households, self.needs)

        self.firm_system.update_cashflow(self.firms)
        self.firm_system.check_viability(self.firms)
        active_firm_ids = {firm.firm_id for firm in self.firms if firm.active}
        active_workers = {worker for firm in self.firms if firm.active for worker in firm.workers}
        for household in self.households:
            if household.employed_by and household.employed_by not in active_firm_ids:
                household.employed_by = None
            if household.household_id not in active_workers:
                household.employed_by = None

        recipe_lookup = {
            recipe_id: Firm(
                firm_id=recipe_id,
                cash=100.0,
                recipe=recipe,
                wage=5.0,
                workers_needed=self.config.workers_per_firm,
            )
            for recipe_id, recipe in self.recipes.items()
        }
        self.firm_system.consider_entry(self.firms, self.market.prices, recipe_lookup)
        if step % 5 == 0:
            self._place_buildings()

        if step % 10 == 0:
            self._log_state(step)

    def _place_buildings(self) -> None:
        zoning = {
            "forestry": ["Forest"],
            "farming": ["FertileLand"],
            "waterworks": ["River"],
            "mining": ["Ore"],
        }
        for firm in self.firms:
            if not firm.active:
                continue
            if firm.cash < 30.0:
                continue
            building_type = firm.recipe.recipe_id
            allowed = zoning.get(building_type, ["Empty"])
            spot = self.world.find_empty_tile(allowed, self.rng)
            if spot:
                self.world.place_building(spot[0], spot[1], building_type)
                firm.cash -= 20.0

    def _log_state(self, step: int) -> None:
        unemployed = sum(1 for h in self.households if h.employed_by is None)
        avg_cash = sum(h.cash for h in self.households) / len(self.households)
        active_firms = sum(1 for f in self.firms if f.active)
        print(
            f"Tick {step}: prices={self.market.prices} unemployed={unemployed} "
            f"avg_cash={avg_cash:.1f} firms={active_firms}"
        )

    def run(self) -> None:
        for step in range(1, self.config.ticks + 1):
            self.tick(step)


def run_simulation(ticks: int, seed: int, world_width: int, world_height: int) -> Simulation:
    config = SimulationConfig(
        ticks=ticks,
        seed=seed,
        households=12,
        workers_per_firm=2,
        world_width=world_width,
        world_height=world_height,
    )
    simulation = Simulation(data_path=Path("data"), config=config)
    simulation.run()
    return simulation


if __name__ == "__main__":
    run_simulation(ticks=200, seed=42, world_width=20, world_height=20)
