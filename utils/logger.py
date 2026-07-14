from datetime import datetime


def log(message):

    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    print(f"[{now}] {message}")