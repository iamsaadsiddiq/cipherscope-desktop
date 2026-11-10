import json

from cipherscope import cli


def test_cli_hash_and_analysis(tmp_path, capsys):
    file = tmp_path / "sample"
    file.write_bytes(b"abc")
    assert cli.main(["hash", str(file)]) == 0
    assert len(capsys.readouterr().out.strip()) == 64
    assert cli.main(["analyze", str(file)]) == 0
    assert json.loads(capsys.readouterr().out)["size"] == 3


def test_cli_sbox(capsys):
    assert cli.main(["sbox"]) == 0
    assert json.loads(capsys.readouterr().out)["nonlinearity"] == 112
