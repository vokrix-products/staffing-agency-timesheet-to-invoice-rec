#!/usr/bin/env python3
import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

def parse_time(t):
    try:
        return datetime.strptime(t, '%H:%M')
    except ValueError:
        return datetime.strptime(t, '%H:%M:%S')

def compute_hours(row):
    if 'hours' in row:
        return Decimal(row['hours'].strip())
    elif 'clock_in' in row and 'clock_out' in row:
        start = parse_time(row['clock_in'].strip())
        end = parse_time(row['clock_out'].strip())
        diff = (end - start).total_seconds() / 3600.0
        return Decimal(str(round(diff, 2)))
    else:
        raise ValueError("Cannot determine hours from timesheet row")

def read_csv(filename):
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def main():
    parser = argparse.ArgumentParser(description='Timesheet to Invoice Reconciliation')
    parser.add_argument('--timesheet', required=True, help='Timesheet CSV file')
    parser.add_argument('--invoice', required=True, help='Invoice CSV file')
    parser.add_argument('--workers', help='Optional workers CSV with rates')
    args = parser.parse_args()

    # Read inputs
    timesheet_rows = read_csv(args.timesheet)
    invoice_rows = read_csv(args.invoice)
    workers = {}
    if args.workers:
        workers = {r['worker_id']: Decimal(r['rate']) for r in read_csv(args.workers)}

    # Prepare output containers
    reconciliation = []
    discrepancies = []
    invoices = []

    # Build index of invoice by worker_id (or name)
    invoice_index = {}
    for inv in invoice_rows:
        key = inv.get('worker_id') or inv.get('Worker ID') or inv.get('worker_name')
        if key:
            invoice_index[key] = inv

    for row in timesheet_rows:
        worker_id = row.get('worker_id') or row.get('Worker ID') or row.get('worker_name')
        worker_name = row.get('worker_name') or row.get('Worker Name') or str(worker_id)

        # Compute hours
        hours = compute_hours(row)

        # Determine rate
        rate = None
        if worker_id and worker_id in workers:
            rate = workers[worker_id]
        elif 'rate' in row:
            rate = Decimal(row['rate'].strip())
        else:
            rate = Decimal('0')  # fallback

        # Compute billing
        billing = (hours * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Get invoice amount if exists
        inv = invoice_index.get(worker_id) or invoice_index.get(worker_name)
        invoice_amount = None
        if inv:
            amount_field = inv.get('amount') or inv.get('billing') or inv.get('total')
            if amount_field:
                invoice_amount = Decimal(amount_field.strip())
        else:
            invoice_amount = Decimal('0')

        # Determine reconciliation status and detail
        diff = (billing - invoice_amount).copy_abs() if invoice_amount is not None else Decimal('0')
        discrepancy_detected = diff > Decimal('0.01')
        if discrepancy_detected:
            status = 'discrepancy:critical'
            detail = f"Mismatch: computed billing {billing:.2f} vs invoiced {invoice_amount:.2f}, difference {diff:.2f}"
        else:
            status = 'reconciled:good'
            detail = 'No discrepancy'

        # Build reconciliation row
        rec_row = {
            'Worker Name': worker_name,
            'Worker ID': worker_id,
            'Hours': str(hours),
            'Rate': str(rate),
            'Computed Billing': str(billing),
            'Invoice Amount': str(invoice_amount) if invoice_amount is not None else '',
            'Difference': str(diff),
            'Status': status,
            'Details': detail
        }
        reconciliation.append(rec_row)

        if discrepancy_detected:
            discrepancies.append(rec_row)

        invoices.append(rec_row)

    # Write reconciliation full output
    rec_fields = ['Worker Name', 'Worker ID', 'Hours', 'Rate', 'Computed Billing', 'Invoice Amount', 'Difference', 'Status', 'Details']
    with open('reconciliation.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rec_fields)
        writer.writeheader()
        writer.writerows(reconciliation)

    # Write discrepancy CSV (only rows with discrepancy:critical)
    if discrepancies:
        with open('discrepancy.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rec_fields)
            writer.writeheader()
            writer.writerows(discrepancies)
    else:
        # Create empty file with header
        with open('discrepancy.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rec_fields)
            writer.writeheader()

    # Write invoice CSV (all rows)
    inv_fields = ['Worker Name', 'Worker ID', 'Computed Billing', 'Invoice Amount', 'Status']
    with open('invoice.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=inv_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(invoices)

    print("Reconciliation complete. Output files: reconciliation.csv, discrepancy.csv, invoice.csv")

if __name__ == '__main__':
    main()
