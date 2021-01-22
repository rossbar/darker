# pylint: disable=too-many-arguments

"""Unit tests for :mod:`darker.linting`"""

from pathlib import Path

import pytest

from darker.git import RevisionRange
from darker.linting import _parse_linter_line, run_linter


@pytest.mark.kwparametrize(
    dict(line="module.py:42: Description", expect=(Path("module.py"), 42)),
    dict(line="module.py:42:5: Description", expect=(Path("module.py"), 42)),
    dict(line="no-linenum.py: Description", expect=(None, None)),
    dict(line="mod.py:invalid-linenum:5: Description", expect=(None, None)),
    dict(line="invalid linter output", expect=(None, None)),
)
def test_parse_linter_line(git_repo, monkeypatch, line, expect):
    """Linter output is parsed correctly"""
    monkeypatch.chdir(git_repo.root)
    result = _parse_linter_line(line, git_repo.root)
    assert result == expect


@pytest.mark.kwparametrize(
    dict(
        _descr="No files to check, no output",
        paths=[],
        location="test.py:1:",
        expect=[],
    ),
    dict(
        _descr="Check one file, report on a modified line in test.py",
        paths=["one.py"],
        location="test.py:1:",
        expect=["test.py:1: {git_repo.root}/one.py"],
    ),
    dict(
        _descr="Check one file, report on a column of a modified line in test.py",
        paths=["one.py"],
        location="test.py:1:42:",
        expect=["test.py:1:42: {git_repo.root}/one.py"],
    ),
    dict(
        _descr="No output if report is on an unmodified line in test.py",
        paths=["one.py"],
        location="test.py:2:42:",
        expect=[],
    ),
    dict(
        _descr="No output if report is on a column of an unmodified line in test.py",
        paths=["one.py"],
        location="test.py:2:42:",
        expect=[],
    ),
    dict(
        _descr="Check two files, rpeort on a modified line in test.py",
        paths=["one.py", "two.py"],
        location="test.py:1:",
        expect=["test.py:1: {git_repo.root}/one.py {git_repo.root}/two.py"],
    ),
    dict(
        _descr="Check two files, rpeort on a column of a modified line in test.py",
        paths=["one.py", "two.py"],
        location="test.py:1:42:",
        expect=["test.py:1:42: {git_repo.root}/one.py {git_repo.root}/two.py"],
    ),
    dict(
        _descr="No output if 2-file report is on an unmodified line in test.py",
        paths=["one.py", "two.py"],
        location="test.py:2:",
        expect=[],
    ),
    dict(
        _descr="No output if 2-file report is on a column of an unmodified line",
        paths=["one.py", "two.py"],
        location="test.py:2:42:",
        expect=[],
    ),
)
def test_run_linter(git_repo, monkeypatch, capsys, _descr, paths, location, expect):
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
    monkeypatch.chdir(git_repo.root)
    cmdline = f"echo {location}"

    run_linter(
        cmdline, Path(git_repo.root), {Path(p) for p in paths}, RevisionRange("HEAD")
    )

    # We can now verify that the linter received the correct paths on its command line
    # by checking standard output from the our `echo` "linter".
    # The test cases also verify that only linter reports on modified lines are output.
    result = capsys.readouterr().out.splitlines()
    assert result == [line.format(git_repo=git_repo) for line in expect]
