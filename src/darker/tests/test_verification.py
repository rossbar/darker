"""Unit tests for :mod:`darker.verification`"""

from typing import List

import pytest

from darker.utils import DiffChunk, TextDocument
from darker.verification import BinarySearch, NotEquivalentError, verify_ast_unchanged


@pytest.mark.parametrize(
    "src_content, dst_content, expect",
    [
        ("if True: pass", ["if False: pass"], AssertionError),
        ("if True: pass", ["if True:", "    pass"], None),
    ],
)
def test_verify_ast_unchanged(src_content, dst_content, expect):
    black_chunks: List[DiffChunk] = [(1, ("black",), ("chunks",))]
    edited_linenums = [1, 2]
    try:
        verify_ast_unchanged(
            TextDocument.from_lines([src_content]),
            TextDocument.from_lines(dst_content),
            black_chunks,
            edited_linenums,
        )
    except NotEquivalentError:
        assert expect is AssertionError
    else:
        assert expect is None


def test_binary_search_premature_result():
    """``darker.verification.BinarySearch``"""
    with pytest.raises(RuntimeError):

        _ = BinarySearch(0, 5).result


def test_binary_search():
    """``darker.verification.BinarySearch``"""
    search = BinarySearch(0, 5)
    tries = []
    while not search.found:
        tries.append(search.get_next())

        search.respond(tries[-1] > 2)

    assert search.result == 3
    assert tries == [0, 3, 2]
