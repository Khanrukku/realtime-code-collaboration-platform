from app.collab.models import CommittedOperation, Operation
from app.collab.transform import transform_against

def test_insert_insert_tie_break_is_deterministic():
    committed = CommittedOperation(
        type="insert",
        position=0,
        base_version=0,
        text="A",
        client_id="a",
        version=1,
    )
    incoming = Operation(
        type="insert",
        position=0,
        base_version=0,
        text="B",
        client_id="b",
    )

    result = transform_against(incoming, committed)
    assert result.position == 1

def test_insert_moves_left_after_prior_delete():
    committed = CommittedOperation(
        type="delete",
        position=2,
        base_version=0,
        length=2,
        client_id="a",
        version=1,
    )
    incoming = Operation(
        type="insert",
        position=6,
        base_version=0,
        text="X",
        client_id="b",
    )

    result = transform_against(incoming, committed)
    assert result.position == 4
