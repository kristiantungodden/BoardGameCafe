class VippsError(Exception):
    pass


class VippsTransientError(VippsError):
    pass


class VippsPermanentError(VippsError):
    pass
