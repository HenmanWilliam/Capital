import argparse

from capital.sim import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Capital simulation core.")
    parser.add_argument("--ticks", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    run_simulation(ticks=args.ticks, seed=args.seed)


if __name__ == "__main__":
    main()
