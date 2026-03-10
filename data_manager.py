# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, Any
from astrbot.api import logger

# 🚀 强制 Path 包装，杜绝返回值类型不一致导致的路径拼接崩溃
try:
    from astrbot.core.utils.astrbot_path import get_astrbot_data_path
    BASE_PATH = Path(get_astrbot_data_path())
except ImportError:
    BASE_PATH = Path.cwd() / "data"

class MiHomeDataManager:
    def __init__(self, plugin_name: str):
        self.data_dir = BASE_PATH / "plugin_data" / plugin_name
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.auth_path = self.data_dir / "auth.json"
        self.state_path = self.data_dir / "state.json"

    def get_auth_path(self) -> str:
        # 向下兼容底层依赖 mijiaAPI，要求必须是字符串
        return str(self.auth_path)

    def auth_exists(self) -> bool:
        return self.auth_path.exists()

    def clear_auth_file(self) -> bool:
        if self.auth_exists():
            try:
                self.auth_path.unlink()
                return True
            except Exception as e:
                logger.error(f"[MiHome] 文件移除失败: {e}")
                return False
        return False

    def load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            with self.state_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"[MiHome] 状态文件读取忽略: {e}")
            return {}

    def save_state(self, state: Dict[str, Any]) -> None:
        try:
            with self.state_path.open("w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[MiHome] 状态保存失败: {e}")

    def update_state(self, **kwargs) -> None:
        state = self.load_state()
        state.update(kwargs)
        self.save_state(state)
