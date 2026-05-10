import argparse
import json
from datetime import datetime

from app.logging_config import configure_logging
from app.db import session_scope
from app.services.analytics import AnalyticsService
from app.services.caption import CaptionService
from app.services.orchestrator import TriggerOrchestrator
from app.services.seed import SeedService
from app.services.telegram import TelegramService
from app.services.weekly import WeeklyReviewService

configure_logging()


def main() -> None:
    parser = argparse.ArgumentParser(prog="elise-content-os")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed")

    trigger_parser = subparsers.add_parser("trigger")
    trigger_parser.add_argument("trigger_time", choices=["morning", "afternoon", "evening"])
    trigger_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("weekly-review")

    subparsers.add_parser("openai-smoke")

    analytics_parser = subparsers.add_parser("analytics")
    analytics_subparsers = analytics_parser.add_subparsers(dest="analytics_command", required=True)
    analytics_add = analytics_subparsers.add_parser("add")
    analytics_add.add_argument("--plan-id")
    analytics_add.add_argument("--platform-post-url")
    analytics_add.add_argument("--published-at")
    analytics_add.add_argument("--content-format", required=True)
    analytics_add.add_argument("--reach", type=int)
    analytics_add.add_argument("--likes", type=int)
    analytics_add.add_argument("--comments", type=int)
    analytics_add.add_argument("--saves", type=int)
    analytics_add.add_argument("--shares", type=int)
    analytics_add.add_argument("--replies", type=int)
    analytics_add.add_argument("--follower-count-snapshot", type=int)

    args = parser.parse_args()

    if args.command == "seed":
        with session_scope() as session:
            result = SeedService(session).seed_all()
        print(json.dumps({"status": "ok", **result}, indent=2))
        return

    if args.command == "trigger":
        with session_scope() as session:
            result = TriggerOrchestrator(session).run_trigger(args.trigger_time, dry_run=args.dry_run)
        print(json.dumps(result.model_dump(), indent=2))
        return

    if args.command == "weekly-review":
        with session_scope() as session:
            review = WeeklyReviewService(session).create_review()
        try:
            TelegramService().send_admin_alert("Weekly review", review.summary)
        except Exception:
            pass
        print(json.dumps({"status": "created", "review_id": review.id}, indent=2))
        return

    if args.command == "openai-smoke":
        try:
            result = CaptionService().smoke_test()
            print(json.dumps({"status": "ok", "result": result.model_dump()}, indent=2))
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "error_type": "openai_failure",
                        "error": str(exc),
                    },
                    indent=2,
                )
            )
            raise SystemExit(1)
        return

    if args.command == "analytics" and args.analytics_command == "add":
        with session_scope() as session:
            snapshot = AnalyticsService(session).add_snapshot(
                plan_id=args.plan_id,
                platform_post_url=args.platform_post_url,
                published_at=datetime.fromisoformat(args.published_at) if args.published_at else None,
                content_format=args.content_format,
                reach=args.reach,
                likes=args.likes,
                comments=args.comments,
                saves=args.saves,
                shares=args.shares,
                replies=args.replies,
                follower_count_snapshot=args.follower_count_snapshot,
            )
        print(json.dumps({"status": "created", "analytics_snapshot_id": snapshot.id}, indent=2))
        return


if __name__ == "__main__":
    main()
