import pytest
import asyncio
import functools
from conversify.main import entrypoint, prewarm
from livekit.agents import Worker, SimulateJobInfo, WorkerOptions
from conversify.utils.config import ConfigManager

import os

@pytest.mark.asyncio
async def test_agent_simulation():
    """
    Test that the ConversifyAgent can be simulated without errors.
    This test will initialize a worker and run a simulated job.
    """
    os.environ["LIVEKIT_URL"] = "http://localhost:7880"
    os.environ["LIVEKIT_API_KEY"] = "devkey"
    os.environ["LIVEKIT_API_SECRET"] = "secret"
    config = ConfigManager().load_config()

    entrypoint_with_config = functools.partial(entrypoint, config=config)
    prewarm_with_config = functools.partial(prewarm, config=config)

    opts = WorkerOptions(
        entrypoint_fnc=entrypoint_with_config,
        prewarm_fnc=prewarm_with_config,
        initialize_process_timeout=300,
    )

    worker = Worker(
        opts,
        devmode=True,
        register=False, # don't register with a livekit server
    )

    # Run the worker in a background task
    worker_task = asyncio.create_task(worker.run())

    # wait for the worker to start
    await asyncio.sleep(1)

    try:
        # Simulate a job
        await worker.simulate_job(
            SimulateJobInfo(room="test-room", participant_identity="test-participant")
        )

        # Let the job run for a bit
        await asyncio.sleep(5)

    finally:
        # aclose will cancel the worker_task
        await worker.aclose()
        # wait for the task to finish
        await worker_task
