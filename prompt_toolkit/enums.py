
class LineMode(object):
    """
    State of the `Line` object.
    """
    NORMAL = 'normal'
    INCREMENTAL_SEARCH = 'incremental-search'
    COMPLETE = 'complete'


class IncrementalSearchDirection:
    FORWARD = 'forward'
    BACKWARD = 'backward'

