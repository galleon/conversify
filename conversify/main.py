import asyncio
import functools
import logging
import os
from typing import Any

import aiohttp as _aiohttp
from dotenv import load_dotenv
from openai import AsyncClient

__orig_ClientSession = _aiohttp.ClientSession


def _ClientSession_no_proxy(*args, **kwargs):  # noqa: N802
    proxy = kwargs.pop("proxy", None)  # livekit-agents 1.2.6 passes this (unsupported)
    if proxy:  # optional: map to env so requests still use the proxy
        os.environ.setdefault("HTTP_PROXY", proxy)
        os.environ.setdefault("HTTPS_PROXY", proxy)
        kwargs.setdefault("trust_env", True)
    return __orig_ClientSession(*args, **kwargs)


_aiohttp.ClientSession = _ClientSession_no_proxy

from livekit.agents import (  # noqa: E402
    AgentSession,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
)
from livekit.agents.types import NOT_GIVEN  # noqa: E402
from livekit.plugins import noise_cancellation, silero, simli  # noqa: E402
from livekit.plugins.turn_detector.multilingual import MultilingualModel  # noqa: E402

from conversify.core.agent import ConversifyAgent  # noqa: E402
from conversify.core.callbacks import metrics_callback, shutdown_callback  # noqa: E402
from conversify.core.vision import video_processing_loop  # noqa: E402
from conversify.models.llm import OpenaiLLM  # noqa: E402
from conversify.models.stt import WhisperSTT  # noqa: E402
from conversify.models.tts import KokoroTTS  # noqa: E402
from conversify.utils.config import ConfigManager  # noqa: E402
from conversify.utils.logger import setup_logging  # noqa: E402

logger = logging.getLogger(__name__)


def prewarm(proc: JobProcess, config: dict[str, Any]):
    """Prewarms resources needed by the agent, like the VAD model."""
    logger.info("Prewarming VAD...")
    vad_config = config["vad"]

    proc.userdata["vad"] = silero.VAD.load(
        min_speech_duration=vad_config["min_speech_duration"],
        min_silence_duration=vad_config["min_silence_duration"],
        prefix_padding_duration=vad_config["prefix_padding_duration"],
        max_buffered_speech=vad_config["max_buffered_speech"],
        activation_threshold=vad_config["activation_threshold"],
        force_cpu=vad_config["force_cpu"],
        sample_rate=vad_config["sample_rate"],
    )
    logger.info("VAD prewarmed successfully.")


async def entrypoint(ctx: JobContext, config: dict[str, Any]):
    """The main entrypoint for the agent job."""
    # Setup initial logging context
    ctx.log_context_fields = {
        "room": ctx.room.name,
        "job_id": ctx.job.id,
    }
    logger.info(f"Agent entrypoint started. Context: {ctx.log_context_fields}")

    await ctx.connect()
    logger.info("Successfully connected to room.")

    # Create shared state dictionary for inter-task communication
    shared_state: dict[str, Any] = {}

    # Initialize LLM Client here using config
    llm_config = config["llm"]
    try:
        llm_client = AsyncClient(
            api_key=llm_config["api_key"], base_url=llm_config["base_url"]
        )
        logger.info(f"Initialized LLM Client at {llm_config['base_url']}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM Client: {e}")
        raise

    # Check if VAD was prewarmed successfully
    vad = ctx.proc.userdata.get("vad")
    if not vad:
        logger.error("VAD not found in process userdata. Exiting.")
        return

    # Setup the AgentSession with configured plugins
    session = AgentSession(
        vad=vad,
        llm=OpenaiLLM(client=llm_client, config=config),
        stt=WhisperSTT(config=config),
        tts=KokoroTTS(config=config),
        turn_detection=MultilingualModel() if config["agent"]["use_eou"] else NOT_GIVEN,
        resume_false_interruption=False,
    )
    logger.info("AgentSession created.")

    # Start the video processing loop if configured
    video_task: asyncio.Task | None = None
    vision_config = config["vision"]

    if vision_config["use"]:
        logger.info("Starting video processing loop...")
        video_task = asyncio.create_task(
            video_processing_loop(
                ctx, shared_state, vision_config["video_frame_interval"]
            )
        )

    # Setup metrics collection
    metrics_callback(session)

    # Wait for a participant to join before starting the session
    logger.info("Waiting for participant to join...")
    participant = await ctx.wait_for_participant()
    logger.info(
        f"Participant '{participant.identity if participant else 'unknown'}' joined."
    )

    # setup agent instance
    agent = ConversifyAgent(
        participant_identity=participant.identity,
        shared_state=shared_state,
        config=config,
    )

    # Register the shutdown callback
    ctx.add_shutdown_callback(lambda: shutdown_callback(agent, video_task))
    logger.info("Shutdown callback registered.")

    # Add a virtual avatar to the session, if desired
    if config["agent"]["use_avatar"]:
        simli_api_key = os.getenv("SIMLI_API_KEY")
        simli_face_id = os.getenv("SIMLI_FACE_ID")

        if not simli_api_key or not simli_face_id:
            raise RuntimeError(
                "Missing SIMLI_API_KEY or SIMLI_FACE_ID in environment. "
                "Set them in .env.local (and ensure agent.env_file points to it)."
            )

        simli_avatar = simli.AvatarSession(
            simli_config=simli.SimliConfig(
                api_key=simli_api_key,
                face_id=simli_face_id,
            ),
        )

        await simli_avatar.start(session, room=ctx.room)

    # Start the agent session
    logger.info("Starting agent session...")
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
            if config["agent"]["use_background_noise_removal"]
            else None,
        ),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    if config["agent"]["use_background_audio"]:
        background_audio = BackgroundAudioPlayer(
            # play office ambience sound looping in the background
            ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.8),
            # play keyboard typing sound when the agent is thinking
            thinking_sound=[
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
            ],
        )

        await background_audio.start(room=ctx.room, agent_session=session)


def main():
    """Main function that initializes and runs the applicaton."""
    # Configure basic logging BEFORE loading config
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    initial_logger = logging.getLogger(__name__)
    initial_logger.info("Basic logging configured. Loading configuration...")

    # Load configuration
    app_config = ConfigManager().load_config()
    initial_logger.info("Configuration loaded.")

    # Load env variables
    load_dotenv(app_config["agent"]["env_file"])

    # Setup centralized logging using the dedicated function
    setup_logging(config=app_config, project_root=ConfigManager().project_root)

    # Now, get the properly configured logger for the main module
    logger = logging.getLogger(__name__)  # Re-get logger after setup
    logger.info("Centralized logging configured. Starting LiveKit Agent application...")

    # Create a partial function that includes the config
    entrypoint_with_config = functools.partial(entrypoint, config=app_config)
    prewarm_with_config = functools.partial(prewarm, config=app_config)

    logger.info(f"prewarm_with_config: {prewarm_with_config}")

    # Define worker options using loaded config
    worker_config = app_config["worker"]
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint_with_config,
        prewarm_fnc=prewarm_with_config,
        job_memory_warn_mb=worker_config["job_memory_warn_mb"],
        load_threshold=worker_config["load_threshold"],
        job_memory_limit_mb=worker_config["job_memory_limit_mb"],
    )
    logger.info(f"worker_options: {worker_options}")

    # Run the CLI application
    cli.run_app(worker_options)


if __name__ == "__main__":
    main()
