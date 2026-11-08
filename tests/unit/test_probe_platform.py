"""Verdicts du script de mesure de l'hébergeur et date de construction de l'image."""

from __future__ import annotations

from pathlib import Path

from scripts.probe_platform import Reply, background_verdict, impossible
from scripts.release import build_time


def _task(started: str, finished: str | None, seconds: float = 20) -> dict[str, object]:
    return {
        "instance": "a:1",
        "tache": {"lancee_le": started, "duree_s": seconds, "terminee_le": finished},
    }


def test_a_failed_request_is_never_read_as_a_result() -> None:
    assert impossible(Reply(200, 0.1, {})) is None
    assert impossible(Reply(200, 0.1, {}), Reply(502, 1.2, {}, "HTTP 502")) == (
        "mesure impossible (HTTP 502 après 1 s)"
    )
    assert impossible(Reply(None, 30, {}, "TimeoutError")) == (
        "mesure impossible (TimeoutError après 30 s)"
    )


def test_a_task_finished_late_reveals_a_frozen_process() -> None:
    on_time = _task("2026-11-05T10:00:00+00:00", "2026-11-05T10:00:21+00:00")
    assert background_verdict(on_time, on_time) == "exécutée jusqu'au bout, à l'heure"
    # Gelé 8 s par la plateforme (SIGSTOP), puis réveillé : terminée quand même.
    late = _task("2026-11-05T10:00:00+00:00", "2026-11-05T10:00:28+00:00", seconds=3)
    assert "terminée en retard" in background_verdict(late, late)
    never = _task("2026-11-05T10:00:00+00:00", None)
    assert "pas terminée" in background_verdict(never, never)
    other = {**never, "instance": "b:2"}
    assert background_verdict(never, other).startswith("inconnu")


def test_build_time_is_read_from_the_image(tmp_path: Path) -> None:
    stamp = tmp_path / "BUILD_TIME"
    assert build_time(stamp) is None
    stamp.write_text("1762300000\n", encoding="utf-8")
    assert build_time(stamp) == 1762300000
    stamp.write_text("pas une date", encoding="utf-8")
    assert build_time(stamp) is None
