"""按归属更新业务运行状态，由调用方与相关业务写入一同提交。"""

from uuid import UUID

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from jobpilot.db.models import AiRun, RunStatus


async def set_run_status(
    session: AsyncSession, user_id: UUID, run_id: UUID, status: RunStatus
) -> bool:
    """原子更新未结束的运行；已结束或不属于该用户时返回 False。"""
    active = (RunStatus.RUNNING, RunStatus.WAITING_CONFIRMATION)
    changed = await session.scalar(
        update(AiRun)
        .where(
            AiRun.user_id == user_id, AiRun.run_id == run_id, AiRun.status.in_(active)
        )
        .values(status=status, finished_at=None if status in active else func.now())
        .returning(AiRun.run_id)
    )
    return changed is not None
