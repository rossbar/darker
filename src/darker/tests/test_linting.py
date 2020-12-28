# pylint: disable=too-many-arguments

"""Unit tests for :mod:`darker.linting`"""

from pathlib import Path

import pytest

from darker.git import RevisionRange
from darker.linting import _parse_linter_line, run_linter


@pytest.mark.parametrize(
    "line, expect",
    [
        ("module.py:42: Description", (Path("module.py"), 42)),
        ("module.py:42:5: Description", (Path("module.py"), 42)),
        ("no-linenum.py: Description", (None, None)),
        ("mod.py:invalid-linenum:5: Description", (None, None)),
        ("invalid linter output", (None, None)),
    ],
)
def test_parse_linter_line(git_repo, monkeypatch, line, expect):
    """Linter output is parsed correctly"""
    monkeypatch.chdir(git_repo.root)
    result = _parse_linter_line(line, git_repo.root)
    assert result == expect


@pytest.mark.parametrize(
    "_descr, paths, location, expect_output, expect_log",
    [
        ("No files to check, no output", [], "test.py:1:", [], []),
        (
            "Check one file, report on a modified line in test.py",
            ["one.py"],
            "test.py:1:",
            ["test.py:1: {git_repo.root}/one.py"],
            [],
        ),
        (
            "Check one file, report on a column of a modified line in test.py",
            ["one.py"],
            "test.py:1:42:",
            ["test.py:1:42: {git_repo.root}/one.py"],
            [],
        ),
        (
            "No output if report is on an unmodified line in test.py",
            ["one.py"],
            "test.py:2:42:",
            [],
            [],
        ),
        (
            "No output if report is on a column of an unmodified line in test.py",
            ["one.py"],
            "test.py:2:42:",
            [],
            [],
        ),
        (
            "Check two files, rpeort on a modified line in test.py",
            ["one.py", "two.py"],
            "test.py:1:",
            ["test.py:1: {git_repo.root}/one.py {git_repo.root}/two.py"],
            [],
        ),
        (
            "Check two files, rpeort on a column of a modified line in test.py",
            ["one.py", "two.py"],
            "test.py:1:42:",
            ["test.py:1:42: {git_repo.root}/one.py {git_repo.root}/two.py"],
            [],
        ),
        (
            "No output if 2-file report is on an unmodified line in test.py",
            ["one.py", "two.py"],
            "test.py:2:",
            [],
            [],
        ),
        (
            "No output if 2-file report is on a column of an unmodified line",
            ["one.py", "two.py"],
            "test.py:2:42:",
            [],
            [],
        ),
        (
            "Warning for a file missing from the working tree",
            ["missing.py"],
            "missing.py:1:",
            [],
            ["WARNING Missing file missing.py from echo missing.py:1:"],
        ),
    ],
)
def test_run_linter(
    git_repo, capsys, caplog, _descr, paths, location, expect_output, expect_log
):
    """Linter gets correct paths on command line and outputs just changed lines

    We use ``echo`` as our "linter". It just adds the paths of each file to lint as an
    "error" on a line of ``test.py``. What this test does is the equivalent of e.g.::

    - creating a ``test.py`` such that the first line is modified after the last commit
    - creating and committing ``one.py`` and ``two.py``
    - running::

          $ darker -L 'echo test.py:1:' one.py two.py
          test.py:1: git-repo-root/one.py git-repo-root/two.py

    """
    src_paths = git_repo.add({"test.py": "1\n2\n"}, commit="Initial commit")
    src_paths["test.py"].write("one\n2\n")
    cmdline = f"echo {location}"

    run_linter(
        cmdline, Path(git_repo.root), {Path(p) for p in paths}, RevisionRange("HEAD")
    )

    # We can now verify that the linter received the correct paths on its command line
    # by checking standard output from the our `echo` "linter".
    # The test cases also verify that only linter reports on modified lines are output.
    output = capsys.readouterr().out.splitlines()
    assert output == [line.format(git_repo=git_repo) for line in expect_output]
    logs = [f"{record.levelname} {record.message}" for record in caplog.records]
    assert logs == expect_log


def test_run_linter_on_new_file(git_repo, capsys):
    """``run_linter()`` considers file missing from history as empty

    Passes through all linter errors as if the original file was empty.

    """
    git_repo.add({"file1.py": "1\n"}, commit="Initial commit")
    git_repo.create_tag("initial")
    (git_repo.root / "file2.py").write("1\n2\n")

    run_linter(
        "echo file2.py:1:",
        Path(git_repo.root),
        {Path("file2.py")},
        RevisionRange("initial"),
    )

    output = capsys.readouterr().out.splitlines()
    assert output == [f"file2.py:1: {git_repo.root}/file2.py"]
