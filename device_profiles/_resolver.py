# -*- coding: utf-8 -*-
"""Profile 解析逻辑：型号优先 → 类别兜底 → 全局 fallback。"""

from typing import Any, Dict, List

from ._constants import CATEGORY_NONE, VALID_CATEGORIES
from ._globals import GLOBAL_PROP_MAP, GLOBAL_VAL_MAP, GLOBAL_DISPLAY_MAP
from ._categories import CATEGORY_PROFILES
from ._models import MODEL_PROFILES


def normalize_category(category: str) -> str:
    category = str(category or "").strip()
    return category if category in VALID_CATEGORIES else CATEGORY_NONE


def normalize_model(model: str) -> str:
    return str(model or "").strip()


def get_model_profile(model: str) -> Dict[str, Any]:
    model = normalize_model(model)
    if not model:
        return {}
    return MODEL_PROFILES.get(model, {})


def has_model_profile(model: str) -> bool:
    return bool(get_model_profile(model))


def get_model_hidden_props(model: str) -> List[str]:
    profile = get_model_profile(model)
    return profile.get("hidden_props", [])


def get_category_profile(category: str) -> Dict[str, Any]:
    category = normalize_category(category)
    return CATEGORY_PROFILES.get(category, {})


def resolve_profile(model: str = "", category: str = "") -> Dict[str, Any]:
    model_profile = get_model_profile(model)
    if model_profile:
        return model_profile

    category_profile = get_category_profile(category)
    if category_profile:
        return category_profile

    return {}


def resolve_effective_category(model: str = "", category: str = "") -> str:
    model_profile = get_model_profile(model)
    if model_profile:
        model_category = normalize_category(model_profile.get("category", ""))
        if model_category != CATEGORY_NONE:
            return model_category

    return normalize_category(category)


def get_device_prop_map(model: str = "", category: str = "") -> Dict[str, str]:
    profile = resolve_profile(model=model, category=category)
    return {**GLOBAL_PROP_MAP, **profile.get("prop_map", {})}


def get_device_val_map(model: str = "", category: str = "") -> Dict[str, Any]:
    profile = resolve_profile(model=model, category=category)
    return {**GLOBAL_VAL_MAP, **profile.get("value_map", {})}


def get_device_display_map(model: str = "", category: str = "") -> Dict[str, str]:
    profile = resolve_profile(model=model, category=category)
    return {**GLOBAL_DISPLAY_MAP, **profile.get("display_map", {})}


def get_device_value_display_map(model: str = "", category: str = "") -> Dict[str, Dict]:
    """返回 {属性名: {原始值: 友好展示值}} 映射，用于将原始属性值翻译为中文。"""
    profile = resolve_profile(model=model, category=category)
    return {k: dict(v) for k, v in profile.get("value_display_map", {}).items()}


def get_device_action_map(model: str = "", category: str = "") -> Dict[str, str]:
    profile = resolve_profile(model=model, category=category)
    return profile.get("action_map", {})


def get_reverse_prop_map(model: str = "", category: str = "") -> Dict[str, str]:
    forward_map = get_device_prop_map(model=model, category=category)
    return {v: k for k, v in forward_map.items()}


def get_reverse_action_map(model: str = "", category: str = "") -> Dict[str, str]:
    forward_map = get_device_action_map(model=model, category=category)
    return {v: k for k, v in forward_map.items()}


def get_device_detail_writable_keys(model: str = "", category: str = "") -> List[str]:
    profile = resolve_profile(model=model, category=category)
    return profile.get("detail_writable", [])


def get_device_detail_readable_keys(model: str = "", category: str = "") -> List[str]:
    profile = resolve_profile(model=model, category=category)
    return profile.get("detail_readable", [])


def get_device_detail_actions(model: str = "", category: str = "") -> List[str]:
    profile = resolve_profile(model=model, category=category)
    return profile.get("detail_actions", [])


def get_device_help_examples(model: str = "", category: str = "") -> Dict[str, List[str]]:
    profile = resolve_profile(model=model, category=category)
    return profile.get("help_examples", {})


def get_device_action_examples(model: str = "", category: str = "") -> List[str]:
    profile = resolve_profile(model=model, category=category)
    return profile.get("action_examples", [])


def get_device_help_hints(model: str = "", category: str = "") -> Dict[str, str]:
    profile = resolve_profile(model=model, category=category)
    return profile.get("help_hints", {})
