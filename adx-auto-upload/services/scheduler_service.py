# -*- coding: utf-8 -*-
"""
定时任务调度服务

提供定时任务的注册、执行、状态管理等功能。
支持 cron 表达式解析，当 croniter 库不可用时自动切换到模拟模式。
"""

import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 尝试导入 croniter 库
try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False
    logger.info("未检测到 croniter 库，将使用模拟模式解析 cron 表达式")


class SchedulerService:
    """定时任务调度服务类

    负责定时任务的注册、调度执行和状态管理。
    当 croniter 库不可用时，使用简单的时间间隔模拟 cron 调度。

    Attributes:
        tasks (dict): 任务注册表，键为 task_id，值为任务信息字典
    """

    def __init__(self):
        """初始化调度服务

        创建空的任务注册表。
        """
        self.tasks = {}
        logger.info("SchedulerService 初始化完成，croniter 可用: %s", CRONITER_AVAILABLE)

    def register_task(self, task_id, task_type, crontab_expression, callback_func, config=None):
        """注册定时任务

        将任务信息存入注册表，并计算首次执行时间。

        Args:
            task_id (str): 任务唯一标识
            task_type (str): 任务类型（如 "crawl"、"report"、"clean" 等）
            crontab_expression (str): cron 表达式（如 "0 8 * * *" 表示每天 8 点执行）
            callback_func (callable): 任务执行回调函数，无参数
            config (dict, optional): 任务额外配置。默认为 None

        Raises:
            ValueError: 如果 task_id 已存在
            ValueError: 如果 callback_func 不可调用
        """
        # 校验 task_id 唯一性
        if task_id in self.tasks:
            raise ValueError(f"任务 ID '{task_id}' 已存在，请先取消注册")

        # 校验回调函数
        if not callable(callback_func):
            raise ValueError("callback_func 必须是可调用对象")

        # 计算下次执行时间
        next_run_at = self._calculate_next_run(crontab_expression)

        # 存储任务信息
        task_info = {
            "task_id": task_id,
            "task_type": task_type,
            "crontab": crontab_expression,
            "callback": callback_func,
            "config": config or {},
            "status": "active",           # active / paused / error
            "run_count": 0,               # 成功执行次数
            "error_count": 0,             # 失败次数
            "last_run_at": None,          # 上次执行时间
            "last_result": None,          # 上次执行结果
            "next_run_at": next_run_at,   # 下次执行时间
            "registered_at": datetime.now(),  # 注册时间
        }
        self.tasks[task_id] = task_info

        logger.info("已注册任务: %s (类型: %s, cron: %s, 下次执行: %s)",
                     task_id, task_type, crontab_expression,
                     next_run_at.strftime("%Y-%m-%d %H:%M:%S") if next_run_at else "N/A")

    def unregister_task(self, task_id):
        """取消注册定时任务

        从任务注册表中移除指定任务。

        Args:
            task_id (str): 要取消的任务 ID

        Returns:
            bool: 是否成功取消
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info("已取消注册任务: %s", task_id)
            return True
        logger.warning("未找到任务: %s，取消注册失败", task_id)
        return False

    def run_task(self, task_id):
        """手动执行一次任务

        调用任务的回调函数，记录执行结果和统计信息。

        Args:
            task_id (str): 要执行的任务 ID

        Returns:
            dict: 执行结果，包含 success（是否成功）、result（回调返回值）、
                  error（错误信息，失败时）
        """
        if task_id not in self.tasks:
            logger.error("未找到任务: %s", task_id)
            return {
                "success": False,
                "error": f"任务 '{task_id}' 不存在",
            }

        task_info = self.tasks[task_id]
        callback = task_info["callback"]

        logger.info("开始执行任务: %s (类型: %s)", task_id, task_info["task_type"])
        start_time = time.time()

        try:
            # 调用回调函数
            result = callback()
            elapsed = (time.time() - start_time) * 1000

            # 更新成功统计
            task_info["run_count"] += 1
            task_info["last_run_at"] = datetime.now()
            task_info["last_result"] = result
            task_info["status"] = "active"

            # 更新下次执行时间
            task_info["next_run_at"] = self._calculate_next_run(task_info["crontab"])

            logger.info("任务 '%s' 执行成功，耗时: %.1fms", task_id, elapsed)
            return {
                "success": True,
                "result": result,
                "elapsed_ms": round(elapsed, 2),
            }

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000

            # 更新失败统计
            task_info["error_count"] += 1
            task_info["last_run_at"] = datetime.now()
            task_info["last_result"] = None
            task_info["status"] = "error"

            # 仍然更新下次执行时间
            task_info["next_run_at"] = self._calculate_next_run(task_info["crontab"])

            logger.error("任务 '%s' 执行失败: %s，耗时: %.1fms", task_id, str(e), elapsed)
            return {
                "success": False,
                "error": str(e),
                "elapsed_ms": round(elapsed, 2),
            }

    def run_all_due(self):
        """执行所有到期任务

        遍历任务注册表，检查每个任务是否到期，执行所有到期任务。

        Returns:
            list: 已执行任务的 ID 列表
        """
        now = datetime.now()
        executed_tasks = []

        for task_id, task_info in self.tasks.items():
            # 跳过非活跃状态的任务
            if task_info["status"] == "paused":
                continue

            # 检查任务是否到期
            if self._is_due(task_info):
                logger.info("任务 '%s' 已到期，开始执行", task_id)
                self.run_task(task_id)
                executed_tasks.append(task_id)

        if executed_tasks:
            logger.info("本轮共执行 %d 个到期任务: %s", len(executed_tasks), executed_tasks)
        return executed_tasks

    def get_task_status(self, task_id):
        """获取任务状态

        返回指定任务的详细状态信息。

        Args:
            task_id (str): 任务 ID

        Returns:
            dict: 任务状态字典，包含以下字段：
                - task_id (str): 任务 ID
                - task_type (str): 任务类型
                - crontab (str): cron 表达式
                - last_run_at (str or None): 上次执行时间
                - next_run_at (str or None): 下次执行时间
                - run_count (int): 成功执行次数
                - error_count (int): 失败次数
                - status (str): 当前状态
        """
        if task_id not in self.tasks:
            logger.warning("未找到任务: %s", task_id)
            return None

        task_info = self.tasks[task_id]

        # 格式化时间为字符串，方便序列化
        def fmt_time(dt):
            if dt is None:
                return None
            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return str(dt)

        return {
            "task_id": task_info["task_id"],
            "task_type": task_info["task_type"],
            "crontab": task_info["crontab"],
            "last_run_at": fmt_time(task_info["last_run_at"]),
            "next_run_at": fmt_time(task_info["next_run_at"]),
            "run_count": task_info["run_count"],
            "error_count": task_info["error_count"],
            "status": task_info["status"],
        }

    def list_tasks(self):
        """列出所有已注册的任务

        Returns:
            list: 任务状态字典列表
        """
        result = []
        for task_id in self.tasks:
            status = self.get_task_status(task_id)
            if status:
                result.append(status)
        return result

    def _is_due(self, task_info):
        """判断任务是否到期

        比较当前时间与任务的下次执行时间，判断是否需要执行。

        Args:
            task_info (dict): 任务信息字典，需包含 next_run_at 字段

        Returns:
            bool: 任务是否已到期需要执行
        """
        next_run = task_info.get("next_run_at")
        if next_run is None:
            return False

        now = datetime.now()

        if isinstance(next_run, datetime):
            return now >= next_run

        return False

    def _calculate_next_run(self, crontab_expression):
        """计算下次执行时间

        根据 cron 表达式计算下一次应该执行的时间。
        如果 croniter 可用则使用真实解析；否则使用模拟模式。

        模拟模式下，将 cron 表达式的第一个数字字段（分钟）解析为间隔，
        最小间隔为 1 分钟。

        Args:
            crontab_expression (str): cron 表达式（如 "0 8 * * *" 或 "*/5 * * * *"）

        Returns:
            datetime: 下次执行时间
        """
        now = datetime.now()

        if CRONITER_AVAILABLE:
            # 使用 croniter 精确计算
            try:
                cron = croniter(crontab_expression, now)
                next_run = cron.get_next(datetime)
                return next_run
            except Exception as e:
                logger.warning("croniter 解析表达式 '%s' 失败: %s，回退到模拟模式",
                               crontab_expression, str(e))
                # 回退到模拟模式

        # 模拟模式：解析 cron 表达式的分钟字段作为间隔
        interval_minutes = self._parse_crontab_interval(crontab_expression)
        next_run = now + timedelta(minutes=interval_minutes)
        return next_run

    def _parse_crontab_interval(self, crontab_expression):
        """从 cron 表达式中解析模拟间隔（分钟数）

        简单解析 cron 表达式的分钟字段：
        - "*/N * * * *" => N 分钟
        - "0 * * * *" => 60 分钟
        - "0 0 * * *" => 1440 分钟（每天）
        - 其他情况默认 5 分钟

        Args:
            crontab_expression (str): cron 表达式

        Returns:
            int: 间隔分钟数，最小为 1
        """
        parts = crontab_expression.strip().split()
        if len(parts) < 5:
            logger.warning("cron 表达式格式不正确: %s，使用默认间隔 5 分钟", crontab_expression)
            return 5

        minute_field = parts[0]
        hour_field = parts[1]

        try:
            # 解析分钟字段
            if minute_field.startswith("*/"):
                # 如 "*/5" 表示每 5 分钟
                interval = int(minute_field[2:])
                return max(1, interval)
            elif minute_field == "0" and hour_field == "0":
                # "0 0 * * *" 表示每天执行，模拟为 1440 分钟
                return 1440
            elif minute_field == "0" and hour_field.startswith("*/"):
                # "0 */N * * *" 表示每 N 小时执行
                hour_interval = int(hour_field[2:])
                return max(1, hour_interval * 60)
            elif minute_field == "0":
                # "0 * * * *" 表示每小时执行
                return 60
            else:
                # 其他情况：尝试解析为固定分钟数
                try:
                    val = int(minute_field)
                    if val == 0:
                        return 60  # 整点执行，模拟为 60 分钟间隔
                    return val
                except ValueError:
                    return 5
        except (ValueError, IndexError):
            logger.warning("无法解析 cron 表达式: %s，使用默认间隔 5 分钟", crontab_expression)
            return 5