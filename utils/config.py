# -*- coding: utf-8 -*-
"""
配置工具（向后兼容层）

此模块为旧版代码提供兼容接口，内部使用新的统一配置管理器。
现在所有配置都从 config/application.yaml 加载。
"""

import logging
from .config_manager import config as unified_config


def load_config(config_path="config.yaml"):
    """
    加载配置（向后兼容接口）
    
    注意：此函数现在从统一配置文件 config/application.yaml 加载配置，
    config_path 参数被忽略以保持向后兼容。
    
    Args:
        config_path: 配置文件路径（已废弃，保留仅为兼容性）
    
    Returns:
        配置字典，包含旧版脚本需要的配置项
    """
    # 从统一配置管理器获取配置
    return {
        "input_directory": unified_config.get("paths.input_directory", "his_pic"),
        "output_filename": "extracted_text.docx",
        "log_file": unified_config.get("logging.file_path", "logs/app.log"),
        # PDF提取配置（如果旧版脚本需要）
        "pdf_extraction": unified_config.get_section("pdf_extraction"),
    }


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
