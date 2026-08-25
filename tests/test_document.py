import pytest

from app.collab.document import Document
from app.collab.models import Operation

def op(kind, pos, version, *, text=None, length=None, client="a"):
    return Operation(
        type=kind,
        position=pos,
        base_version=version,
        text=text,
        length=length,
        client_id=client,
    )

def test_insert_and_delete():
    doc = Document()

    doc.apply(op("insert", 0, 0, text="hello"))
    assert doc.text == "hello"
    assert doc.version == 1

    doc.apply(op("delete", 1, 1, length=2))
    assert doc.text == "hlo"
    assert doc.version == 2

def test_stale_insert_transforms_after_prior_insert():
    doc = Document()
    doc.apply(op("insert", 0, 0, text="A", client="a"))
    doc.apply(op("insert", 0, 0, text="B", client="b"))
    assert doc.text == "AB"

def test_insert_shifts_after_prior_delete():
    doc = Document(text="abcd")
    doc.apply(op("delete", 1, 0, length=2, client="a"))
    doc.apply(op("insert", 4, 0, text="X", client="b"))
    assert doc.text == "adX"

def test_future_version_is_rejected():
    doc = Document()
    with pytest.raises(ValueError):
        doc.apply(op("insert", 0, 1, text="x"))
