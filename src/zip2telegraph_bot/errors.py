from __future__ import annotations


class UserVisibleError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def format_user_error(error: UserVisibleError) -> str:
    return f"处理失败: {error.message}\n错误码: {error.code}"

