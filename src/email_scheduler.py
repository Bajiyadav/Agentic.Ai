import asyncio
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EmailBackgroundScheduler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EmailBackgroundScheduler, cls).__new__(cls)
            cls._instance._init_scheduler()
        return cls._instance

    def _init_scheduler(self):
        self.is_running = False
        self.interval_seconds = 900  # 15 minutes
        self.last_run_time: Optional[float] = None
        self.total_sweeps = 0
        self._task: Optional[asyncio.Task] = None

    async def _scheduler_loop(self):
        logger.info("⚡ Background email poller loop started.")
        while self.is_running:
            try:
                self.last_run_time = time.time()
                self.total_sweeps += 1
                logger.info(f"Checking recruiter mailbox for incoming candidate applications (Sweep #{self.total_sweeps})...")
                # Sleep until next scheduled interval
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

    def start(self, interval_seconds: int = 900):
        if not self.is_running:
            self.is_running = True
            self.interval_seconds = interval_seconds
            self._task = asyncio.create_task(self._scheduler_loop())
            logger.info("Background Email Scheduler enabled.")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self._task:
                self._task.cancel()
                self._task = None
            logger.info("Background Email Scheduler disabled.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_running,
            "interval_minutes": self.interval_seconds // 60,
            "total_sweeps": self.total_sweeps,
            "last_sweep": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_run_time)) if self.last_run_time else "None yet",
            "next_scheduled_sweep": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_run_time + self.interval_seconds)) if self.last_run_time and self.is_running else "Inactive"
        }

email_scheduler = EmailBackgroundScheduler()
