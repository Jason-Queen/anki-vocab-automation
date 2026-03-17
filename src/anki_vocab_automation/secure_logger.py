"""
安全日志工具
Secure logging utilities to prevent sensitive information leakage
"""

import re
import logging
from typing import Any, Dict, Union


class SecureLogger:
    """安全日志记录器，自动过滤敏感信息"""

    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        # API Keys and tokens
        (r'api[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9+/=]{10,})', r'api_key="***REDACTED***"'),
        (r"bearer\s+([a-zA-Z0-9+/=]{10,})", r"bearer ***REDACTED***"),
        (r'token["\s]*[:=]["\s]*([a-zA-Z0-9+/=]{10,})', r'token="***REDACTED***"'),
        (r'key["\s]*[:=]["\s]*([a-zA-Z0-9+/=]{20,})', r'key="***REDACTED***"'),
        # Authorization headers
        (r'authorization["\s]*[:=]["\s]*([^"\s]+)', r'authorization="***REDACTED***"'),
        (r'"Authorization":\s*"([^"]+)"', r'"Authorization": "***REDACTED***"'),
        # Passwords
        (r'password["\s]*[:=]["\s]*([^"\s]+)', r'password="***REDACTED***"'),
        (r'passwd["\s]*[:=]["\s]*([^"\s]+)', r'passwd="***REDACTED***"'),
        # Secret keys
        (r'secret[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9+/=]{10,})', r'secret_key="***REDACTED***"'),
        # JWT tokens
        (r"(eyJ[a-zA-Z0-9+/=]+\.[a-zA-Z0-9+/=]+\.[a-zA-Z0-9+/=]+)", r"***JWT_TOKEN_REDACTED***"),
        # Credit card numbers (basic pattern)
        (r"\b(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})\b", r"***CARD_NUMBER_REDACTED***"),
        # Email addresses (optional, depending on privacy requirements)
        # (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r'***EMAIL_REDACTED***'),
    ]

    # 编译正则表达式以提高性能
    COMPILED_PATTERNS = [
        (re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in SENSITIVE_PATTERNS
    ]

    @classmethod
    def sanitize_message(cls, message: str) -> str:
        """
        清理日志消息，移除敏感信息

        Args:
            message: 原始日志消息

        Returns:
            清理后的消息
        """
        if not isinstance(message, str):
            message = str(message)

        sanitized = message

        # 应用所有敏感信息过滤模式
        for pattern, replacement in cls.COMPILED_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理字典中的敏感信息

        Args:
            data: 原始数据字典

        Returns:
            清理后的字典
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}
        sensitive_keys = {
            "api_key",
            "apikey",
            "api-key",
            "token",
            "access_token",
            "refresh_token",
            "password",
            "passwd",
            "pwd",
            "secret",
            "secret_key",
            "secret-key",
            "authorization",
            "auth",
            "private_key",
            "private-key",
        }

        for key, value in data.items():
            key_lower = key.lower()

            if key_lower in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    (
                        cls.sanitize_dict(item)
                        if isinstance(item, dict)
                        else cls.sanitize_message(str(item)) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_message(value)
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def secure_debug(cls, logger: logging.Logger, message: str, *args, **kwargs):
        """
        安全的debug日志记录

        Args:
            logger: 日志记录器
            message: 日志消息
            *args: 位置参数
            **kwargs: 关键字参数
        """
        sanitized_message = cls.sanitize_message(message)
        sanitized_args = [cls.sanitize_message(str(arg)) if isinstance(arg, str) else arg for arg in args]
        logger.debug(sanitized_message, *sanitized_args, **kwargs)

    @classmethod
    def secure_info(cls, logger: logging.Logger, message: str, *args, **kwargs):
        """
        安全的info日志记录

        Args:
            logger: 日志记录器
            message: 日志消息
            *args: 位置参数
            **kwargs: 关键字参数
        """
        sanitized_message = cls.sanitize_message(message)
        sanitized_args = [cls.sanitize_message(str(arg)) if isinstance(arg, str) else arg for arg in args]
        logger.info(sanitized_message, *sanitized_args, **kwargs)

    @classmethod
    def secure_warning(cls, logger: logging.Logger, message: str, *args, **kwargs):
        """
        安全的warning日志记录

        Args:
            logger: 日志记录器
            message: 日志消息
            *args: 位置参数
            **kwargs: 关键字参数
        """
        sanitized_message = cls.sanitize_message(message)
        sanitized_args = [cls.sanitize_message(str(arg)) if isinstance(arg, str) else arg for arg in args]
        logger.warning(sanitized_message, *sanitized_args, **kwargs)

    @classmethod
    def secure_error(cls, logger: logging.Logger, message: str, *args, **kwargs):
        """
        安全的error日志记录

        Args:
            logger: 日志记录器
            message: 日志消息
            *args: 位置参数
            **kwargs: 关键字参数
        """
        sanitized_message = cls.sanitize_message(message)
        sanitized_args = [cls.sanitize_message(str(arg)) if isinstance(arg, str) else arg for arg in args]
        logger.error(sanitized_message, *sanitized_args, **kwargs)


def create_secure_logger(name: str) -> logging.Logger:
    """
    创建配置了安全过滤的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 如果还没有配置处理器
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = SecureLogFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


class SecureLogFormatter(logging.Formatter):
    """安全日志格式化器，自动过滤敏感信息"""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)

    def format(self, record):
        # 清理记录消息
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = SecureLogger.sanitize_message(record.msg)

        # 清理参数
        if hasattr(record, "args") and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(SecureLogger.sanitize_message(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(SecureLogger.sanitize_dict(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)

        return super().format(record)


# 便利函数
def sanitize_for_log(data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
    """
    为日志记录清理数据的便利函数

    Args:
        data: 要清理的数据

    Returns:
        清理后的数据
    """
    if isinstance(data, str):
        return SecureLogger.sanitize_message(data)
    elif isinstance(data, dict):
        return SecureLogger.sanitize_dict(data)
    else:
        return data
