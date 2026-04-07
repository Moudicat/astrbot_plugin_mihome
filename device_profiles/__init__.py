# -*- coding: utf-8 -*-
"""
device_profiles 包入口
"""

from ._constants import (  # noqa: F401
    CATEGORY_NONE,
    CATEGORY_AC,
    CATEGORY_PURIFIER,
    CATEGORY_FAN,
    CATEGORY_COOKER,
    CATEGORY_AIR_FRYER,
    CATEGORY_TH_SENSOR,
    CATEGORY_BODY_SCALE,
    CATEGORY_VACUUM,
    CATEGORY_WATER_HEATER,
    CATEGORY_ROUTER,
    CATEGORY_SWITCH,
    CATEGORY_GAS_SENSOR,
    CATEGORY_DOOR_SENSOR,
    VALID_CATEGORIES,
)

from ._globals import (  # noqa: F401
    GLOBAL_PROP_MAP,
    GLOBAL_VAL_MAP,
    GLOBAL_DISPLAY_MAP,
)

from ._categories import CATEGORY_PROFILES  # noqa: F401
from ._models import MODEL_PROFILES  # noqa: F401

from ._resolver import (  # noqa: F401
    normalize_category,
    normalize_model,
    get_model_profile,
    has_model_profile,
    get_model_hidden_props,
    get_category_profile,
    resolve_profile,
    resolve_effective_category,
    get_device_prop_map,
    get_device_val_map,
    get_device_display_map,
    get_device_value_display_map,
    get_device_action_map,
    get_reverse_prop_map,
    get_reverse_action_map,
    get_device_detail_writable_keys,
    get_device_detail_readable_keys,
    get_device_detail_actions,
    get_device_help_examples,
    get_device_action_examples,
    get_device_help_hints,
)
