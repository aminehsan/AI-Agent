from agents import RunConfig


def get_run_compaction_config() -> RunConfig:
    return RunConfig(tracing_disabled=True)
