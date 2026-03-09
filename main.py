# -*- coding: utf-8 -*-
import json
import shlex
import re
from typing import Any

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

from .data_manager import MiHomeDataManager
from .mihome_client import MiHomeClient, MiHomeAuthError, MiHomeControlError, MiHomeClientError

@register("astrbot_plugin_mihome", "RyanVaderAn", "米家云端智能管家", "v6.1.3")
class MiHomeControlPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config or {}
        self.data_manager = MiHomeDataManager("astrbot_plugin_mihome")
        self.client = MiHomeClient(self.data_manager)
        self.action_alias = {"开": True, "开启": True, "打开": True, "on": True, "关": False, "关闭": False, "off": False}

    def _parse_device_map(self) -> dict:
        raw = self.config.get("device_map", "{}")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(parsed, dict): return {}
            return {str(k).strip(): str(v).strip() for k, v in parsed.items() if str(v).strip()}
        # 问题 3 修复：提供明确的配置解析警告
        except Exception as e:
            logger.warning(f"[MiHome] device_map JSON 解析失败，请检查 WebUI 配置格式: {e}")
            return {}

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("米家登录")
    async def mihome_login(self, event: AstrMessageEvent):
        yield event.plain_result("⏳ 正在拉起独立沙盒环境...")
        async def cb(url): await event.send(MessageEventResult().message(f"🔔 请扫码授权：\n\n{url}"))
        res = await self.client.login(qr_callback=cb)
        s = res.get("status")
        msg = {"success": "🎉 授权成功！", "timeout": "❌ 超时了。", "qrcode_not_found": "⚠️ 未能抓取到有效链接。", "already_logged_in": "✅ 您已处于登录状态。"}.get(s, f"❌ 错误: {res.get('message')}")
        yield event.plain_result(msg)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("米家状态")
    async def mihome_status(self, event: AstrMessageEvent):
        s = await self.client.get_login_status()
        yield event.plain_result(f"📊 状态报告：\n- 凭证存在: {s['auth_exists']}\n- 最近登录: {s['last_login_at'] or '无'}\n- 最近异常: {s['last_login_error'] or '无'}\n- 最近控制: {s['last_control_device']} ({'失败' if s['last_control_error'] else '成功'})")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("刷新米家")
    async def refresh_mihome_devices(self, event: AstrMessageEvent):
        yield event.plain_result("⏳ 正在与云端同步设备列表...")
        try:
            devs = await self.client.get_devices()
            if not devs: yield event.plain_result("✅ 拉取成功，但未发现可用设备。"); return
            res = [f"✅ 找到 {len(devs)} 个设备："]
            for i, d in enumerate(devs[:15], 1):
                res.append(f"{i}. 【{d.get('name')}】({d.get('did')}) [{'🟢' if d.get('isOnline') else '🔴'}]")
            yield event.plain_result("\n".join(res))
        except Exception as e: yield event.plain_result(f"❌ 同步失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("控制米家")
    async def control_mihome_device(self, event: AstrMessageEvent, query: str = "", args: Any = None):
        device_map = self._parse_device_map()
        msg = event.message_str.strip()
        parts = shlex.split(re.sub(r'^/?控制米家\s*', '', msg))
        if len(parts) < 2: yield event.plain_result("❌ 格式：/控制米家 [设备] [开/关]"); return
        
        name, act = " ".join(parts[:-1]).strip(), parts[-1].lower()
        if name not in device_map or act not in self.action_alias:
            yield event.plain_result(f"❌ 找不到设备 '{name}'。请检查 WebUI 配置。"); return

        yield event.plain_result(f"⏳ 正在下发【{name}】指令...")
        try:
            await self.client.control_power(device_map[name], self.action_alias[act], name)
            yield event.plain_result("✅ 成功！")
        except MiHomeAuthError:
            yield event.plain_result("❌ 鉴权失效，请重新登录。")
        except MiHomeControlError as e:
            err = str(e)
            if err == "device_not_found": yield event.plain_result("❌ 云端无此设备。请检查：\n1. DID 是否正确\n2. 共享设备权限是否受限")
            elif err == "device_rejected": yield event.plain_result("❌ 设备已在线但拒绝了该操作（可能型号不支持通用开关）。")
            else: yield event.plain_result(f"❌ 控制失败: {err}")
        except MiHomeClientError as e:
            yield event.plain_result(f"❌ API 异常: {e}")
        except Exception as e:
            yield event.plain_result(f"❌ 未知错误: {e}")

    async def terminate(self): await self.client.terminate()
