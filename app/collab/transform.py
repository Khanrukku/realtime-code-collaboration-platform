from copy import deepcopy
from app.collab.models import CommittedOperation, Operation

def transform_against(op: Operation, committed: CommittedOperation) -> Operation:
    out = deepcopy(op)

    if committed.type == "insert":
        inserted = len(committed.text or "")

        if out.type == "insert":
            if (
                committed.position < out.position
                or (
                    committed.position == out.position
                    and committed.client_id <= out.client_id
                )
            ):
                out.position += inserted
        else:
            if committed.position <= out.position:
                out.position += inserted
            elif committed.position < out.position + (out.length or 0):
                out.length = (out.length or 0) + inserted

    else:
        deleted = committed.length or 0
        start = committed.position
        end = start + deleted

        if out.type == "insert":
            if out.position >= end:
                out.position -= deleted
            elif start < out.position < end:
                out.position = start
        else:
            out_start = out.position
            out_end = out.position + (out.length or 0)

            if out_end <= start:
                return out

            if out_start >= end:
                out.position -= deleted
                return out

            overlap_start = max(out_start, start)
            overlap_end = min(out_end, end)
            overlap = max(0, overlap_end - overlap_start)

            if out_start >= start:
                out.position = start

            out.length = max(0, (out.length or 0) - overlap)

    return out
