class MemeError(StandardError):
    pass

class NotFoundError(MemeError):
    pass

class InvalidAccountCancel(MemeError):
    pass
