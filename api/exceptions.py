class ApiError(Exception):
    def __init__(self, message: str, status:int =500):
        super().__init__(message)
        self.status = status