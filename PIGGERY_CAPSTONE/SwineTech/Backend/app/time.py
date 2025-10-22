# app/util/time.py (new small helper)
from datetime import datetime

def utcnow_naive():
    # Naive UTC (no tzinfo), rounded seconds optional to keep JSON pretty
    return datetime.utcnow().replace(microsecond=0)
