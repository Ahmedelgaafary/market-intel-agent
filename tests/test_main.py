from types import SimpleNamespace

from market_intel import main


def test_run_scheduled_agent_registers_monitoring_job(monkeypatch):
    config = SimpleNamespace(schedule=object())
    model = object()
    expected_result = {"run_id": "test-run", "status": "completed"}
    captured = {}

    def fake_run_once(*, config, model):
        captured["run_config"] = config
        captured["run_model"] = model
        return expected_result

    def fake_start_scheduler(*, job, schedule):
        captured["job"] = job
        captured["schedule"] = schedule

    monkeypatch.setattr(main, "load_config", lambda path: config)
    monkeypatch.setattr(main, "run_once", fake_run_once)
    monkeypatch.setattr(main, "start_scheduler", fake_start_scheduler)

    main.run_scheduled_agent(model=model, config_path="test-config.yaml")

    assert captured["schedule"] is config.schedule

    result = captured["job"]()

    assert result == expected_result
    assert captured["run_config"] is config
    assert captured["run_model"] is model
