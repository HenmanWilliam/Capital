from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


GoodId = str


@dataclass
class Inventory:
    goods: Dict[GoodId, float] = field(default_factory=dict)

    def add(self, good: GoodId, quantity: float) -> None:
        if quantity <= 0:
            return
        self.goods[good] = self.goods.get(good, 0.0) + quantity

    def remove(self, good: GoodId, quantity: float) -> float:
        if quantity <= 0:
            return 0.0
        available = self.goods.get(good, 0.0)
        taken = min(available, quantity)
        remaining = available - taken
        if remaining <= 0:
            self.goods.pop(good, None)
        else:
            self.goods[good] = remaining
        return taken

    def get(self, good: GoodId) -> float:
        return self.goods.get(good, 0.0)


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    inputs: Dict[GoodId, float]
    outputs: Dict[GoodId, float]
    labor_required: int


@dataclass
class MarketOrder:
    agent_id: str
    good: GoodId
    quantity: float
    is_buy: bool


@dataclass
class MarketAllocation:
    agent_id: str
    good: GoodId
    quantity: float
    total_price: float
    is_buy: bool


@dataclass
class Household:
    household_id: str
    cash: float
    inventory: Inventory = field(default_factory=Inventory)
    unmet_needs: int = 0
    employed_by: Optional[str] = None


@dataclass
class Firm:
    firm_id: str
    cash: float
    recipe: Recipe
    wage: float
    workers_needed: int
    workers: List[str] = field(default_factory=list)
    inventory: Inventory = field(default_factory=Inventory)
    active: bool = True


@dataclass
class MarketState:
    prices: Dict[GoodId, float]
    min_price: float = 0.5
    max_price: float = 50.0
    k: float = 0.1
