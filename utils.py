from datetime import datetime, timedelta


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

    def get_str_yyyy_mm_dd(self):
        return self.strftime('%Y-%m-%d')

    # def get_datetime_from_yyyy_mm_dd(yyyy_mm__dd: str):
    #     return
