from studio import cli, __version__
from studio.paths import data_dir, workspace


def test_version(capsys):
    assert cli.main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out


def test_data_dir_env(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "d"))
    assert data_dir() == tmp_path / "d"


def test_workspace_creates_dirs(tmp_path):
    ws = workspace(tmp_path)
    assert ws.input.is_dir() and ws.work.is_dir() and ws.output.is_dir()
