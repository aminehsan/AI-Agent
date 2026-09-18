from sys import stdout
from agents import RunResult


def set_output(result: RunResult) -> None:
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")
    answer = result.final_output.strip()
    usage = result.context_wrapper.usage
    print(f"\nAnswer:\n{answer}")
    print(
        "\n"
        "Token usage:\n"
        f"\tinput={usage.input_tokens}\n"
        f"\toutput={usage.output_tokens}\n"
        f"\ttotal={usage.total_tokens}"
    )
