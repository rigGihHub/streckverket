"""Runtime smoke harness for Streckverket's Streamlit shell.

Uses Streamlit's official AppTest when Streamlit is installed. The harness deliberately
renders three shell states: normal, expert, and specialist. It does not press network/API
buttons, so a smoke run should be deterministic and must not require external data.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SmokeMode = Literal["normal", "expert", "specialist"]
APP_FILE = Path(__file__).with_name("app.py")


@dataclass(frozen=True)
class SmokeResult:
    mode: SmokeMode
    exception_count: int
    error_count: int
    tab_count: int
    start_action_count: int = 0
    demo_notice_count: int = 0

    @property
    def ok(self) -> bool:
        shell_ok = (
            self.tab_count == 0 and self.start_action_count == 1
            if self.mode == "normal" else self.tab_count == 19
        )
        return self.exception_count == 0 and self.error_count == self.demo_notice_count and shell_ok


def available() -> bool:
    try:
        from streamlit.testing.v1 import AppTest  # noqa: F401
    except ImportError:
        return False
    return True


def run_smoke(mode: SmokeMode = "normal", timeout: int = 20) -> SmokeResult:
    if mode not in ("normal", "expert", "specialist"):
        raise ValueError(f"Okänt smoke-läge: {mode}")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as exc:
        raise RuntimeError("Streamlit saknas. Installera requirements.txt innan runtime-smoketest körs.") from exc

    at = AppTest.from_file(str(APP_FILE), default_timeout=timeout).run()
    if mode in ("expert", "specialist"):
        if not at.toggle:
            raise AssertionError("Expert-toggle saknas i appskalet.")
        at.toggle[0].set_value(True)
        at.run()
    if mode == "specialist":
        if len(at.toggle) < 2:
            raise AssertionError("Specialist-toggle saknas efter att Expertläge aktiverats.")
        at.toggle[1].set_value(True)
        at.run()

    return SmokeResult(
        mode=mode,
        exception_count=len(at.exception),
        error_count=len(at.error),
        tab_count=len(at.tabs),
        start_action_count=sum(button.key == "landing_fetch_coupon" for button in at.button),
        demo_notice_count=sum(
            error.value == "**HÄMTA RIKTIG KUPONG** — Du tittar på testdata. Systemet är bara till för att prova appen."
            for error in at.error
        ),
    )


def run_all(timeout: int = 20) -> list[SmokeResult]:
    return [run_smoke(mode, timeout=timeout) for mode in ("normal", "expert", "specialist")]


if __name__ == "__main__":
    if not available():
        raise SystemExit("Streamlit saknas. Installera requirements.txt innan runtime-smoketest körs.")
    results = run_all()
    for result in results:
        print(f"{result.mode}: {'OK' if result.ok else 'FAIL'} | exceptions={result.exception_count} errors={result.error_count} tabs={result.tab_count}")
    raise SystemExit(0 if all(r.ok for r in results) else 1)
