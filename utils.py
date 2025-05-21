import yaml
import logging
import os  # Added for default config path if needed, though not strictly used in current load_config for path creation

# Default configuration values
DEFAULT_CONFIG = {
    "input_directory": "his_pic",
    "output_filename": "extracted_text.docx",
    "log_file": "app.log",
}


def load_config(config_path="config.yaml"):
    """Load configuration from a YAML file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        # Ensure all keys are present, using defaults if not
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    except FileNotFoundError:
        # Create a default config if not found
        # This print is fine here as logging isn't set up yet.
        print(
            f"Warning: '{config_path}' not found. Created a default config file. Using default values."
        )
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True)
        return DEFAULT_CONFIG.copy()  # Return a copy
    except Exception as e:
        # This print is fine here as logging isn't set up yet.
        print(f"Error loading config file '{config_path}': {e}. Using default values.")
        return DEFAULT_CONFIG.copy()  # Return a copy of defaults on any other error


def setup_logging(log_file_path, logger_name="app_logger"):
    """Configure logging to file and console, and return the logger instance."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Prevent passing to root logger if it has handlers

    # Remove existing handlers to prevent duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # File handler
    try:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback to console if file handler fails
        print(
            f"Error setting up file logger for '{log_file_path}': {e}. Logging to console only for this handler."
        )

    # Console handler
    console_handler = logging.StreamHandler()
    # Make console logs a bit more concise
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger
