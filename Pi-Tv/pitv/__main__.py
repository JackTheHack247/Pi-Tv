import sys


def main() -> int:
    if sys.platform == "win32":
        print("Pi-TV is for Raspberry Pi with the official TV HAT.")
        print("It cannot receive live TV on Windows.")
        print()
        print("Copy this folder to your Pi, then run:")
        print("  ./scripts/install-pi.sh")
        print("  pitv")
        return 1

    from .app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
