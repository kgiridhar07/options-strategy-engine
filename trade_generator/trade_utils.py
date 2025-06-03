from datetime import datetime
import datetime

def get_options_expiry_dates():
    """
    Calculates and returns potential options expiry dates.

    Assumes weekly options expire on Fridays.
    - "Current week expiry": The Friday of the current week. If today is Saturday or Sunday,
                             it will be the upcoming Friday.
    - "15 days or close by": The first Friday on or after 15 days from today.
    - "30 days or close by": The first Friday on or after 30 days from today.
    - "45 days or close by": The first Friday on or after 45 days from today.

    Returns:
        dict: A dictionary with keys mapping to datetime.date objects:
              - 'current_week_friday_expiry'
              - 'friday_expiry_near_15_days'
              - 'friday_expiry_near_30_days'
              - 'friday_expiry_near_45_days'
    """
    today = datetime.date.today()

    def get_upcoming_friday(base_date):
        days_until_friday = (4 - base_date.weekday() + 7) % 7
        return base_date + datetime.timedelta(days=days_until_friday)

    current_week_expiry = get_upcoming_friday(today)
    date_plus_15_days = today + datetime.timedelta(days=15)
    expiry_15_days = get_upcoming_friday(date_plus_15_days)
    date_plus_30_days = today + datetime.timedelta(days=30)
    expiry_30_days = get_upcoming_friday(date_plus_30_days)
    date_plus_45_days = today + datetime.timedelta(days=45)
    expiry_45_days = get_upcoming_friday(date_plus_45_days)

    return {
        "current_week_friday_expiry": current_week_expiry,
        "friday_expiry_near_15_days": expiry_15_days,
        "friday_expiry_near_30_days": expiry_30_days,
        "friday_expiry_near_45_days": expiry_45_days,
    }