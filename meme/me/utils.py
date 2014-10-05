def validate_id(id):
    id = str(id)
    if len(id) > 128 or len(id) < 1:
        return False
    return True
