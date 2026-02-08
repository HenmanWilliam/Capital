import argparse

from capital.sim import run_simulation
from capital.visual import run_visual_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Capital simulation core.")
    parser.add_argument("--ticks", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--visual", action="store_true", help="Run the visual simulation UI.")
    parser.add_argument("--width", type=int, default=20)
    parser.add_argument("--height", type=int, default=20)
    parser.add_argument("--tick-ms", type=int, default=200)
    args = parser.parse_args()

    if args.visual:
        run_visual_simulation(
            ticks=args.ticks,
            seed=args.seed,
            world_width=args.width,
            world_height=args.height,
            tick_ms=args.tick_ms,
        )
    else:
        run_simulation(
            ticks=args.ticks,
            seed=args.seed,
            world_width=args.width,
            world_height=args.height,
        )


if __name__ == "__main__":
    main()
