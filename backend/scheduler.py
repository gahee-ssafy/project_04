"""
주간 학습일지 자동 생성 스케줄러
- 매주 토요일 오전 7:00 KST (Asia/Seoul)
- 모든 유저의 AI 분석 자동 재생성
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def run_weekly_reports():
    """전체 유저 주간 학습일지 재생성."""
    from database import get_all_user_ids
    from services.report import generate_report

    user_ids = get_all_user_ids()
    logger.info(f"[주간 학습일지] 시작 — 대상 유저 {len(user_ids)}명")

    for user_id in user_ids:
        try:
            generate_report(user_id, regenerate=True)
            logger.info(f"[주간 학습일지] user_id={user_id} 완료")
        except Exception as e:
            logger.error(f"[주간 학습일지] user_id={user_id} 실패: {e}")

    logger.info("[주간 학습일지] 전체 완료")


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        run_weekly_reports,
        trigger=CronTrigger(
            day_of_week="sat",   # 토요일
            hour=7,              # 오전 7시
            minute=0,
            timezone="Asia/Seoul",
        ),
        id="weekly_report",
        name="주간 학습일지 자동 생성",
        replace_existing=True,
    )
    return scheduler
