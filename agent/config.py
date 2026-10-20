from agents import RunConfig


def get_run_summarizer_config() -> RunConfig:
    return RunConfig(tracing_disabled=True)
