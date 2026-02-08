from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from .model import Firm, Household, MarketAllocation, MarketOrder, MarketState


@dataclass
class LaborMatchResult:
    hired: Dict[str, str]


class LaborSystem:
    def match(self, households: List[Household], firms: List[Firm]) -> LaborMatchResult:
        hired: Dict[str, str] = {}
        available_households = [h for h in households if h.employed_by is None]
        available_households.sort(key=lambda h: h.household_id)

        firms_with_openings = [f for f in firms if f.active and len(f.workers) < f.workers_needed]
        firms_with_openings.sort(key=lambda f: f.wage, reverse=True)

        for firm in firms_with_openings:
            openings = firm.workers_needed - len(firm.workers)
            while openings > 0 and available_households:
                household = available_households.pop(0)
                household.employed_by = firm.firm_id
                firm.workers.append(household.household_id)
                hired[household.household_id] = firm.firm_id
                openings -= 1
        return LaborMatchResult(hired=hired)

    def adjust_wages(self, firms: List[Firm]) -> None:
        for firm in firms:
            if not firm.active:
                continue
            if len(firm.workers) < firm.workers_needed:
                firm.wage *= 1.02
            elif len(firm.workers) > firm.workers_needed:
                firm.wage *= 0.99


class ProductionSystem:
    def produce(self, firms: Iterable[Firm]) -> None:
        for firm in firms:
            if not firm.active:
                continue
            if len(firm.workers) < firm.recipe.labor_required:
                continue
            can_produce = True
            for good, qty in firm.recipe.inputs.items():
                if firm.inventory.get(good) < qty:
                    can_produce = False
                    break
            if not can_produce:
                continue
            for good, qty in firm.recipe.inputs.items():
                firm.inventory.remove(good, qty)
            for good, qty in firm.recipe.outputs.items():
                firm.inventory.add(good, qty)


class MarketSystem:
    def update_prices(self, state: MarketState, orders: List[MarketOrder]) -> None:
        demand: Dict[str, float] = {}
        supply: Dict[str, float] = {}
        for order in orders:
            if order.is_buy:
                demand[order.good] = demand.get(order.good, 0.0) + order.quantity
            else:
                supply[order.good] = supply.get(order.good, 0.0) + order.quantity

        for good, price in list(state.prices.items()):
            d = demand.get(good, 0.0)
            s = supply.get(good, 0.0)
            excess = d - s
            adjusted = price * (1 + state.k * excess / max(1.0, s))
            state.prices[good] = min(state.max_price, max(state.min_price, adjusted))

    def clear_market(self, state: MarketState, orders: List[MarketOrder]) -> List[MarketAllocation]:
        allocations: List[MarketAllocation] = []
        demand_by_good: Dict[str, List[MarketOrder]] = {}
        supply_by_good: Dict[str, List[MarketOrder]] = {}
        for order in orders:
            if order.is_buy:
                demand_by_good.setdefault(order.good, []).append(order)
            else:
                supply_by_good.setdefault(order.good, []).append(order)

        for good, buy_orders in demand_by_good.items():
            sell_orders = supply_by_good.get(good, [])
            total_demand = sum(o.quantity for o in buy_orders)
            total_supply = sum(o.quantity for o in sell_orders)
            if total_supply <= 0 and total_demand <= 0:
                continue

            price = state.prices[good]
            if total_demand > 0:
                buy_ratio = min(1.0, total_supply / total_demand) if total_demand > 0 else 0.0
                for order in buy_orders:
                    qty = order.quantity * buy_ratio
                    if qty <= 0:
                        continue
                    allocations.append(
                        MarketAllocation(
                            agent_id=order.agent_id,
                            good=order.good,
                            quantity=qty,
                            total_price=qty * price,
                            is_buy=True,
                        )
                    )
            if total_supply > 0:
                sell_ratio = min(1.0, total_demand / total_supply) if total_supply > 0 else 0.0
                for order in sell_orders:
                    qty = order.quantity * sell_ratio
                    if qty <= 0:
                        continue
                    allocations.append(
                        MarketAllocation(
                            agent_id=order.agent_id,
                            good=order.good,
                            quantity=qty,
                            total_price=qty * price,
                            is_buy=False,
                        )
                    )
        return allocations


class ConsumptionSystem:
    def create_orders(self, households: Iterable[Household], needs: Dict[str, float]) -> List[MarketOrder]:
        orders: List[MarketOrder] = []
        for household in households:
            for good, qty in needs.items():
                current = household.inventory.get(good)
                if current < qty:
                    orders.append(
                        MarketOrder(
                            agent_id=household.household_id,
                            good=good,
                            quantity=qty - current,
                            is_buy=True,
                        )
                    )
        return orders

    def consume(self, households: Iterable[Household], needs: Dict[str, float]) -> None:
        for household in households:
            unmet = 0
            for good, qty in needs.items():
                consumed = household.inventory.remove(good, qty)
                if consumed < qty:
                    unmet += 1
            household.unmet_needs = unmet


class FirmSystem:
    def __init__(self, base_prices: Dict[str, float]) -> None:
        self.base_prices = base_prices

    def update_cashflow(self, firms: Iterable[Firm]) -> None:
        for firm in firms:
            if not firm.active:
                continue
            payroll = firm.wage * len(firm.workers)
            firm.cash -= payroll

    def check_viability(self, firms: Iterable[Firm]) -> None:
        for firm in firms:
            if not firm.active:
                continue
            if firm.cash < -10:
                firm.active = False
                firm.workers.clear()

    def consider_entry(self, firms: List[Firm], prices: Dict[str, float], recipe_lookup: Dict[str, Firm]) -> None:
        existing_outputs = {f.recipe.recipe_id for f in firms if f.active}
        for recipe_id, firm_template in recipe_lookup.items():
            if recipe_id in existing_outputs:
                continue
            output_good = next(iter(firm_template.recipe.outputs.keys()))
            if prices.get(output_good, 0) > self.base_prices.get(output_good, 1.0) * 1.2:
                new_firm = Firm(
                    firm_id=f"firm_{len(firms) + 1}",
                    cash=50.0,
                    recipe=firm_template.recipe,
                    wage=firm_template.wage,
                    workers_needed=firm_template.workers_needed,
                )
                firms.append(new_firm)
