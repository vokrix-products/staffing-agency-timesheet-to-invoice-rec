#!/usr/bin/env python3
"""
Poller for the staffing agency timesheet-to-invoice reconciliation pipeline.
Calls reconciliation.reconcile with file paths provided as command-line arguments.
"""
import sys
import argparse
from reconciliation import reconcile

def main():
    parser = argparse.ArgumentParser(
        description="Run timesheet-to-invoice reconciliation."
    )
    parser.add_argument("client_timesheet", help="Path to client timesheet CSV")
    parser.add_argument("agency_internal", help="Path to agency internal CSV")
    parser.add_argument("rate_agreement", help="Path to rate agreement CSV or PDF")
    parser.add_argument("--output-discrepancy", help="Write discrepancy report to CSV")
    parser.add_argument("--output-invoice", help="Write reconciled invoice to CSV")
    args = parser.parse_args()

    discrepancy_report, reconciled_invoice = reconcile(
        args.client_timesheet, args.agency_internal, args.rate_agreement
    )

    if args.output_discrepancy:
        discrepancy_report.to_csv(args.output_discrepancy, index=False)
        print(f"Discrepancy report written to {args.output_discrepancy}")

    if args.output_invoice:
        reconciled_invoice.to_csv(args.output_invoice, index=False)
        print(f"Reconciled invoice written to {args.output_invoice}")

    if discrepancy_report.empty:
        print("No discrepancies found. All rows reconciled:good.")
    else:
        print(f"Found {len(discrepancy_report)} row(s) with discrepancies (status: discrepancy:critical).")

    non_discrepancy = reconciled_invoice[reconciled_invoice["status"] == "reconciled:good"]
    print(f"Reconciled rows (status: reconciled:good): {len(non_discrepancy)}")
    sys.exit(0)

if __name__ == "__main__":
    main()
