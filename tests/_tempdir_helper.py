"""Temporary-directory helper for unit tests.

Works around DSH workspace-write sandbox restrictions: Python's `tempfile`
uses Windows short paths (`ADMINI~1`) that the sandbox treats as outside
the workspace, causing PermissionError. When running under DSH, tests
create temporary directories under the workspace instead.
"""
import contextlib
import pathlib
import shutil
import tempfile
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _tempfile_works():
    """Probe whether Python's tempfile works in the current environment."""
    try:
        with tempfile.TemporaryDirectory() as temp:
            p = pathlib.Path(temp) / "probe"
            p.write_text("ok")
            p.unlink()
        return True
    except PermissionError:
        return False


_TEMPFILE_WORKS = _tempfile_works()


@contextlib.contextmanager
def test_tempdir():
    """Yield a temporary directory path, safe for DSH sandbox."""
    if _TEMPFILE_WORKS:
        with tempfile.TemporaryDirectory() as temp:
            yield pathlib.Path(temp)
    else:
        # DSH sandbox workaround: use workspace-local directory.
        base = ROOT / ".test-tmp"
        base.mkdir(exist_ok=True)
        path = base / f"test-{uuid.uuid4().hex[:12]}"
        path.mkdir()
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)
