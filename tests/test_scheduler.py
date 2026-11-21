from market_intel.config import ScheduleConfig
from market_intel.scheduler import start_scheduler


def test_scheduler_registers_weekly_job(monkeypatch):
    captured = {}

    class FakeScheduler:
        def __init__(self, timezone):
            captured["timezone"] = timezone

        def add_job(self, function, **kwargs):
            captured["function"] = function
            captured["job"] = kwargs

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(
        "market_intel.scheduler.BlockingScheduler",
        FakeScheduler,
    )

    schedule = ScheduleConfig(
        day="monday",
        hour=9,
        minute=0,
        timezone="Africa/Cairo",
    )

    start_scheduler(job=lambda: "ok", schedule=schedule)

    assert captured["timezone"].key == "Africa/Cairo"
    assert captured["job"]["trigger"] == "cron"
    assert captured["job"]["day_of_week"] == "mon"
    assert captured["job"]["hour"] == 9
    assert captured["job"]["minute"] == 0
    assert captured["job"]["max_instances"] == 1
    assert captured["job"]["coalesce"] is True
    assert captured["started"] is True


def test_scheduler_job_handles_failure(monkeypatch):
    captured = {}

    class FakeScheduler:
        def __init__(self, timezone):
            pass

        def add_job(self, function, **kwargs):
            captured["function"] = function

        def start(self):
            captured["function"]()

    monkeypatch.setattr(
        "market_intel.scheduler.BlockingScheduler",
        FakeScheduler,
    )

    schedule = ScheduleConfig(
        day="monday",
        hour=9,
        minute=0,
        timezone="UTC",
    )

    start_scheduler(
        job=lambda: (_ for _ in ()).throw(RuntimeError("test failure")),
        schedule=schedule,
    )
