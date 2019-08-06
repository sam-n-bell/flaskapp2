import datetime


def convert_timedelta_to_string(timedelta, time_format):
    timedelta = datetime.datetime.strptime(str(timedelta), time_format)
    timedelta = datetime.datetime.strftime(timedelta, time_format)
    return timedelta
