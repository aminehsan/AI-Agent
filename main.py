from asyncio import run
from sys import stdin, stdout
from runner import run_agent


if __name__ == "__main__":
    if hasattr(stdin, "reconfigure"):
        stdin.reconfigure(encoding="utf-8")
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")
    run(run_agent())
