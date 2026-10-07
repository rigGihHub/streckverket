from pathlib import Path

import release_info

ROOT = Path(__file__).resolve().parent


def test_release_is_v382_or_newer():
    assert tuple(map(int, release_info.APP_VERSION.split('.'))) >= (3, 82, 0)
    assert release_info.RELEASE_NAME


def test_windows_double_click_launcher_exists():
    launcher = (ROOT / 'STARTA_STRECKVERKET.bat').read_text(encoding='utf-8')
    assert 'streamlit run app.py' in launcher
    assert '.venv' in launcher
    assert 'requirements.txt' in launcher


def test_container_deployment_files_exist_and_are_safe():
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    render = (ROOT / 'render.yaml').read_text(encoding='utf-8')
    gitignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
    assert 'streamlit run app.py' in dockerfile
    assert '${PORT:-8501}' in dockerfile
    assert '/_stcore/health' in dockerfile
    assert 'STRECKVERKET_DATABASE_URL' in render
    assert '.streamlit/secrets.toml' in gitignore
    assert '*.db' in gitignore


def test_app_uses_release_info_instead_of_stale_hardcoded_caption():
    app = (ROOT / 'app.py').read_text(encoding='utf-8')
    assert 'from release_info import APP_VERSION, RELEASE_NAME' in app
    assert 'v3.75.0 · STRECKVERKET TEXT-TV' not in app
    assert 'APP_VERSION' in app and 'RELEASE_NAME' in app


def test_deployment_docs_warn_about_ephemeral_sqlite():
    doc = (ROOT / 'DEPLOYMENT_READY_v3.82.md').read_text(encoding='utf-8')
    assert 'ephemeral' in doc.lower()
    assert 'STRECKVERKET_DATABASE_URL' in doc
