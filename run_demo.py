import tempfile, os, sys
import pandas as pd
from reconciliation import reconcile

def main():
    client_data = """worker_id,date,hours_approved
W001,2025-01-06,8.0
W001,2025-01-07,8.0
W002,2025-01-06,7.5
W002,2025-01-07,8.0
"""
    agency_data = """worker_id,date,hours_submitted,rate_used
W001,2025-01-06,8.0,25.0
W001,2025-01-07,7.5,25.0
W002,2025-01-06,8.0,30.0
W002,2025-01-07,8.0,30.0
"""
    rate_data = """worker_id,worker_name,rate
W001,Alice Smith,25.0
W002,Bob Jones,30.0
"""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "client.csv"), "w") as f:
            f.write(client_data)
        with open(os.path.join(tmp, "agency.csv"), "w") as f:
            f.write(agency_data)
        with open(os.path.join(tmp, "rates.csv"), "w") as f:
            f.write(rate_data)
        disc, invo = reconcile(
            os.path.join(tmp, "client.csv"),
            os.path.join(tmp, "agency.csv"),
            os.path.join(tmp, "rates.csv")
        )
        print("DISCREPANCY REPORT")
        print(disc.to_string(index=False))
        print("\nRECONCILED INVOICE")
        print(invo.to_string(index=False))
    sys.exit(0)

if __name__ == "__main__":
    main()
