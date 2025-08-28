import os
import logging
import tomllib
from typing import Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages configuration loading, parsing, path resolution,
    and prompt loading for the Conversify application.
    """

    def __init__(self, config_path: str = 'config.toml'):
        """Initialize the ConfigManager with a path to the TOML config file."""
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.project_root = self._get_project_root()

    def _get_project_root(self) -> str:
        """Get the absolute path to the project root directory."""
        # Assuming this file is in 'utils' subdirectory of the project root
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _resolve_path(self, relative_path: str) -> str:
        """Convert a relative path to an absolute path based on project root."""
        return os.path.abspath(os.path.join(self.project_root, relative_path))

    def _load_toml_config(self) -> dict[str, Any]:
        """Load the TOML configuration file."""
        abs_config_path = self._resolve_path(self.config_path)
        logger.info(f"Loading configuration from: {abs_config_path}")

        try:
            with open(abs_config_path, 'rb') as f:
                config = tomllib.load(f)
                if not isinstance(config, dict):
                    raise ValueError("Configuration file does not contain a valid TOML table")
                logger.info(f"Configuration loaded successfully from {abs_config_path}")
                return config
        except Exception as e:
            logger.error(f"Error loading TOML configuration {abs_config_path}: {e}")
            raise

    def _load_prompt(self, prompt_path: str) -> str:
        """Load prompt content from a file."""
        abs_prompt_path = self._resolve_path(prompt_path)
        logger.info(f"Loading prompt from: {abs_prompt_path}")

        try:
            with open(abs_prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.info(f"Prompt loaded successfully from {abs_prompt_path}")
                return content
        except Exception as e:
            logger.error(f"Error loading prompt from {abs_prompt_path}: {e}")
            raise

    def _resolve_paths_in_config(self) -> None:
        """
        Resolve all relative paths in the configuration to absolute paths.
        Also loads any file content that needs to be loaded (e.g., prompts).
        """
        # ---- agent / prompt
        agent_cfg = self.config.get('agent')
        if not isinstance(agent_cfg, dict):
            raise KeyError("Missing required section: [agent]")

        prompt_file = agent_cfg.get('instructions_file')
        if not prompt_file:
            raise KeyError("Missing required key: agent.instructions_file")
        agent_cfg['instructions'] = self._load_prompt(prompt_file)

        # ---- memory
        memory_cfg = self.config.get('memory', {})
        if memory_cfg.get('use', False):
            memory_dir_rel = memory_cfg.get('dir')
            if not memory_dir_rel:
                raise KeyError("memory.use=true but memory.dir is not set")
            memory_dir_abs = self._resolve_path(memory_dir_rel)
            memory_cfg['dir_abs'] = memory_dir_abs
            logger.info(f"Memory enabled. Directory path: {memory_dir_abs}")
        else:
            logger.info("Memory usage is disabled in config.")
        self.config['memory'] = memory_cfg

        # ---- STT / whisper paths
        stt_cfg = self.config.get('stt', {})
        whisper_cfg = stt_cfg.get('whisper', {})
        mcd = whisper_cfg.get('model_cache_directory')
        if mcd and not os.path.isabs(mcd):
            whisper_cfg['model_cache_directory'] = self._resolve_path(mcd)

        wa = whisper_cfg.get('warmup_audio')
        if wa and not os.path.isabs(wa):
            whisper_cfg['warmup_audio'] = self._resolve_path(wa)

        stt_cfg['whisper'] = whisper_cfg
        self.config['stt'] = stt_cfg

        # ---- logging file path
        logging_cfg = self.config.get('logging', {})
        log_file_rel = logging_cfg.get('file')
        if log_file_rel:
            if not os.path.isabs(log_file_rel):
                logging_cfg['file_abs'] = self._resolve_path(log_file_rel)
        else:
            logger.warning("logging.file not set; file-based logging may be disabled.")
        self.config['logging'] = logging_cfg

    def load_config(self) -> dict[str, Any]:
        """
        Load and process the configuration file.
        Returns the processed configuration dictionary.
        """
        self.config = self._load_toml_config()
        self._resolve_paths_in_config()
        logger.info("Configuration processed successfully.")
        return self.config
