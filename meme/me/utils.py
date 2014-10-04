def check_id(id):
    id = str(id)
    if len(account_id) > 128 or len(account_id) < 1:
        return False
    return True
