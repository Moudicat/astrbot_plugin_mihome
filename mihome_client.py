# -*- coding: utf-8 -*-
import re
import os
import sys
import asyncio
from datetime import datetime
from typing import Any, Dict, Callable, Awaitable, Union

from astrbot.api import logger
from mijiaAPI import (
    mijiaAPI, 
    mijiaDevice,
    LoginError,
    DeviceNotFoundError,
    DeviceSetError,
    APIError
)
from .data_manager import MiHomeDataManager

LOGIN_IDLE = "idle"
LOGIN_RUNNING = "running"

class MiHomeClientError(Exception):
    pass

class MiHomeAuthError(MiHomeClientError):
    pass

class MiHomeControlError(MiHomeClientError):
    pass

class MiHomeClient:
    def __init__(self, data_manager: MiHomeDataManager):
        self.data_manager = data_manager
        self.api = mijiaAPI(self.data_manager.get_auth_path())
        self._api_lock = asyncio.Lock()
        self._login_status = LOGIN_IDLE
        self._login_process: asyncio.subprocess.Process | None = None
        self._worker_script = os.path.join(os.path.dirname(__file__), "_login_worker.py")

    def _check_idle(self):
        if self._login_status != LOGIN_IDLE:
            raise MiHomeClientError("登录沙盒正在运行中，请等待其结束或超时后再试。")

    async def get_login_status(self) -> Dict[str, Any]:
        state = self.data_manager.load_state()
        return {
            "auth_exists": self.data_manager.auth_exists(),
            "login_in_progress": self._login_status != LOGIN_IDLE,
            "last_login_at": state.get("last_login_at", ""),
            "last_login_error": state.get("last_login_error", ""),
            "last_control_error": state.get("last_control_error", ""),
            "last_control_device": state.get("last_control_device", ""),
        }

    async def logout(self) -> bool:
        if self._login_process and self._login_process.returncode is None:
            try:
                self._login_process.kill()
                await self._login_process.wait()
            # 问题 2 修复：不再裸吞，明确排除系统级异常
            except ProcessLookupError: pass
            except Exception: pass
            finally: self._login_process = None

        self._login_status = LOGIN_IDLE 
        ok = self.data_manager.clear_auth_file()
        self.api = mijiaAPI(self.data_manager.get_auth_path())
        if ok:
            self.data_manager.update_state(last_login_at="", last_login_error="", last_control_error="", last_control_device="")
        return ok

    async def login(self, qr_callback: Union[Callable[[str], Awaitable[None]], Callable[[str], None]]) -> Dict[str, Any]:
        if self._login_status != LOGIN_IDLE: return {"status": "in_progress"}
        self._login_status = LOGIN_RUNNING
        qr_found, full_buffer = False, ""
        try:
            async with self._api_lock:
                self._login_process = await asyncio.create_subprocess_exec(sys.executable, "-u", self._worker_script, self.data_manager.get_auth_path(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                if self._login_process.stdout is None: raise MiHomeClientError("管道不可用")
                
                async def read_stdout():
                    nonlocal qr_found, full_buffer
                    while True:
                        chunk = await self._login_process.stdout.read(256)
                        if not chunk: break
                        text = chunk.decode('utf-8', errors='replace')
                        full_buffer += text
                        logger.debug(f"[MiHome][WorkerOutput] {text!r}")
                        
                        if not qr_found:
                            compact = full_buffer.replace("\r", "").replace("\n", "")
                            match = re.search(r'(https://account\.xiaomi\.com/pass/qr/login\?[^\s\'"]+)', compact)
                            if match:
                                url = match.group(1)
                                if "ticket=" in url and "dc=" in url and "sid=" in url:
                                    qr_found = True
                                    logger.info(f"[MiHome] 成功截获完整登录链接: {url}")
                                    if asyncio.iscoroutinefunction(qr_callback): await qr_callback(url)
                                    else: qr_callback(url)
                
                try:
                    await asyncio.wait_for(asyncio.gather(self._login_process.wait(), read_stdout()), timeout=120.0)
                except asyncio.TimeoutError:
                    try:
                        self._login_process.kill()
                        await self._login_process.wait()
                    except ProcessLookupError: pass
                    except Exception: pass
                    
                    msg = "等待扫码确认超时 (120秒)" if qr_found else "未能在超时前提取到登录链接"
                    self.data_manager.update_state(last_login_error=msg)
                    return {"status": "timeout" if qr_found else "qrcode_not_found"}
                
                if self._login_process.returncode == 0:
                    self.data_manager.update_state(last_login_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_login_error="")
                    self.api = mijiaAPI(self.data_manager.get_auth_path())
                    return {"status": "success" if qr_found else "already_logged_in"}
                else:
                    err = full_buffer[-800:].strip()
                    self.data_manager.update_state(last_login_error=err)
                    return {"status": "error", "message": err}
        except Exception as e:
            self.data_manager.update_state(last_login_error=str(e))
            return {"status": "error", "message": str(e)}
        finally:
            self._login_status = LOGIN_IDLE
            self._login_process = None

    async def get_devices(self) -> list[dict]:
        self._check_idle()
        try:
            async with self._api_lock:
                await asyncio.to_thread(self.api.login)
                own = await asyncio.to_thread(self.api.get_devices_list)
                if not isinstance(own, list): own = []
                
                shared = []
                if hasattr(self.api, "get_shared_devices_list"):
                    try:
                        shared = await asyncio.to_thread(self.api.get_shared_devices_list)
                        if not isinstance(shared, list): shared = []
                    except Exception as e:
                        # 问题 4：诊断阶段暂时允许回写，方便查看具体报错
                        logger.warning(f"[MiHome] 获取共享设备列表失败: {e}")
                        self.data_manager.update_state(last_login_error=f"共享设备拉取失败: {e}")
                
                merged = {}
                for d in (own + shared):
                    if isinstance(d, dict) and d.get("did"):
                        merged[str(d["did"]).strip()] = d
                return list(merged.values())
        except LoginError as e:
            self.data_manager.update_state(last_login_error=f"鉴权失效: {e}")
            raise MiHomeAuthError(str(e)) from e
        except APIError as e:
            self.data_manager.update_state(last_login_error=f"云端接口异常: {e}")
            raise MiHomeClientError(str(e)) from e
        except Exception as e:
            self.data_manager.update_state(last_login_error=f"拉取设备列表时未知异常: {e}")
            raise MiHomeClientError(str(e)) from e

    async def control_power(self, did: str, is_on: bool, device_name: str = "") -> None:
        self._check_idle()
        try:
            async with self._api_lock:
                await asyncio.to_thread(self.api.login)
                logger.info(f"[MiHome] 下发控制: {device_name} ({did}) -> {is_on}")
                device = mijiaDevice(self.api, did=did)
                
                # 问题 5：诊断手段，非稳定接口，封装保护
                try:
                    props = await asyncio.to_thread(device.get_props)
                    logger.info(f"[MiHome] 设备 {did} 嗅探结果: {props}")
                except Exception as p_e:
                    logger.warning(f"[MiHome] 设备 {did} 属性嗅探失败 (接口不支持): {p_e}")

                await asyncio.to_thread(device.set, "on", is_on)
            self.data_manager.update_state(last_control_error="", last_control_device=device_name or did)
        except LoginError as e:
            raise MiHomeAuthError(str(e)) from e
        except DeviceNotFoundError as e:
            logger.error(f"[MiHome] 底层确认 DID 不存在: {did}")
            raise MiHomeControlError("device_not_found") from e
        except DeviceSetError as e:
            raise MiHomeControlError("device_rejected") from e
        except APIError as e:
            raise MiHomeClientError(f"云端拒绝请求: {e}") from e
        except Exception as e:
            logger.error(f"[MiHome] 未知控制异常: type={type(e).__name__}, detail={e}")
            self.data_manager.update_state(last_control_error=str(e), last_control_device=device_name or did)
            raise MiHomeControlError(str(e)) from e

    async def terminate(self) -> None:
        if self._login_process and self._login_process.returncode is None:
            try:
                self._login_process.kill()
                await self._login_process.wait()
            except ProcessLookupError: pass
            except Exception: pass
        self.api = None; self._login_status = LOGIN_IDLE; self._login_process = None
