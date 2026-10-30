from asyncio import run

from agent.compaction import compact_session

# from runner import run_agent

if __name__ == "__main__":
    # run_agent()
    run(compact_session())
