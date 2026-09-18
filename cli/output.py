from sys import stdout
from agents import RunResult


def set_output(result: RunResult):
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")
    answer = result.final_output.strip()
    usage = result.context_wrapper.usage
    print(
        "\nUsage:\n"
        f" requests={usage.requests}\n"
        f" input_tokens={usage.input_tokens}\n"
        f" output_tokens={usage.output_tokens}\n"
        f" total_tokens={usage.total_tokens}"
    )
    print(f"\nAnswer:\n{answer}")
