from operonx import op


@op
def case(item: dict) -> dict:
    """The door's item is read once (it is transient); this hands it on to every step."""
    return {"email": item}
