from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Dict, List, Optional, Tuple

TileType = str
BuildingType = str


TILE_TYPES: List[TileType] = ["Forest", "Ore", "FertileLand", "River", "Empty"]


@dataclass
class World:
    width: int
    height: int
    tiles: List[List[TileType]]
    buildings: Dict[Tuple[int, int], BuildingType] = field(default_factory=dict)

    @classmethod
    def generate(cls, width: int, height: int, seed: int) -> "World":
        rng = random.Random(seed)
        tiles = [
            [rng.choices(TILE_TYPES, weights=[0.2, 0.1, 0.2, 0.1, 0.4])[0] for _ in range(width)]
            for _ in range(height)
        ]
        return cls(width=width, height=height, tiles=tiles)

    def tile_at(self, x: int, y: int) -> TileType:
        return self.tiles[y][x]

    def place_building(self, x: int, y: int, building: BuildingType) -> bool:
        if (x, y) in self.buildings:
            return False
        self.buildings[(x, y)] = building
        return True

    def building_counts(self) -> Dict[BuildingType, int]:
        counts: Dict[BuildingType, int] = {}
        for building in self.buildings.values():
            counts[building] = counts.get(building, 0) + 1
        return counts

    def find_empty_tile(self, allowed_tiles: List[TileType], rng: random.Random) -> Optional[Tuple[int, int]]:
        candidates = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.tile_at(x, y) in allowed_tiles and (x, y) not in self.buildings
        ]
        if not candidates:
            return None
        return rng.choice(candidates)
