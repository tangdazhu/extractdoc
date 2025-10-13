import yaml
import logging
import os

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
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    except FileNotFoundError:
        print(
            f"Warning: '{config_path}' not found. Created a default config file. Using default values."
        )
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True)
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"Error loading config file '{config_path}': {e}. Using default values.")
        return DEFAULT_CONFIG.copy()


def setup_logging(log_file_path, logger_name="app_logger"):
    """Configure logging to file and console, and return the logger instance."""
    logger = logging.getLogger("ocr_system")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        try:
            file_handler = logging.FileHandler(log_file_path, encoding="utf-8-sig")
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(
                f"Error setting up file logger for '{log_file_path}': {e}. Logging to console only for this handler."
            )

        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        logger.propagate = False
    else:
        logger.propagate = False

    return logger
