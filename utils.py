from datetime import datetime, timedelta
from typing import Callable


def binary_search(array: list, x, key: Callable):
    lo, hi = 0, len(array)
    while lo < hi:
        mid = (lo + hi) // 2
        if key(array[mid]) <= key(x):
            hi = mid
        else:
            lo = mid + 1
    if lo != len(array) and array[lo] == x:
        return lo
    raise ValueError('Element not found!')

class ExtDate(datetime):

    def _get_near_date(self, is_prev=True, num_days=1):
        """Return prev or next day (or few days) in format YYYY-MM-DD."""
        if is_prev:
            return (self - timedelta(days=num_days)).strftime('%Y-%m-%d')
        else:
            return (self + timedelta(days=num_days)).strftime('%Y-%m-%d')

    def get_prev_day(self, num_days=1):
        """Return date of prev day (or few days) in format YYYY-MM-DD."""
        return self._get_near_date(is_prev=True, num_days=num_days)

    def get_next_day(self, num_days=1):
        """Return date of next day (or few days) in format YYYY-MM-DD."""
        return self._get_near_date(is_prev=False, num_days=num_days)

    def yyyy_mm_dd(self):
        return self.strftime('%Y-%m-%d')
