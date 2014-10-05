class MemeError(StandardError):
    pass

class NotFoundError(MemeError):
    pass

class CancelError(MemeError):
    pass

class BalanceError(MemeError):
    pass

class ConflictedError(MemeError):
    pass

class ValidationError(MemeError):
    pass
