from app.services.analytics import AnalyticsService


def test_manual_analytics_snapshot_insert_read(session):
    snapshot = AnalyticsService(session).add_snapshot(
        plan_id=None,
        content_format="story",
        platform_post_url="https://instagram.com/p/example",
        reach=10,
        likes=2,
        comments=1,
        saves=0,
        shares=0,
        replies=1,
        follower_count_snapshot=100,
    )

    loaded = session.get(type(snapshot), snapshot.id)
    assert loaded is not None
    assert loaded.content_format == "story"
    assert loaded.reach == 10
