from agents import RunConfig


def create_summarizer_run_config() -> RunConfig:
    return RunConfig(tracing_disabled=True)
