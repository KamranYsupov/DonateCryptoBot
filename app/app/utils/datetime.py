from datetime import date, timedelta

def get_start_of_week(day: date = date.today()) -> date:
    start_of_week = day - timedelta(days=day.weekday())
    return start_of_week
