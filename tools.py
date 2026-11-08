import csv
import os


def load_csv_summary(file_name):
    """Summarize a CSV file: return its column names, row count, and numeric columns.

    If the file is missing or cannot be read, return a dict with an
    "error" key instead of raising an exception.
    """
    # Step 1: check that the file exists before trying to open it.
    if not os.path.exists(file_name):
        return {"error": f"File not found: {file_name}"}

    # Step 2: read every row at once (catches bad paths/permissions/encoding errors).
    try:
        with open(file_name, newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        # A file with no rows has no header, so treat it as a read failure.
        if not rows:
            raise ValueError("file is empty")
    except Exception as exc:
        return {"error": f"Could not read {file_name}: {exc}"}

    # Step 3: split the header from the data, dropping fully blank lines.
    header = [name.strip() for name in rows[0]]
    data_rows = [row for row in rows[1:] if any(cell.strip() for cell in row)]

    # Step 4: gather each column's values, padding short rows with "".
    column_values = {name: [] for name in header}
    for row in data_rows:
        for index, name in enumerate(header):
            column_values[name].append(row[index] if index < len(row) else "")

    # Step 5: numeric means it has values and every non-empty one parses as a float.
    numeric_columns = []
    for name, values in column_values.items():
        non_empty = [value.strip() for value in values if value.strip()]
        is_numeric = bool(non_empty)
        for value in non_empty:
            try:
                float(value)
            except ValueError:
                is_numeric = False
                break
        if is_numeric:
            numeric_columns.append(name)

    # Step 6: build the summary in the same shape as before.
    return {
        "columns": header,
        "rows": len(data_rows),
        "numeric_columns": numeric_columns,
    }


if __name__ == "__main__":
    # Small manual test: run this file directly to see the result.
    print(load_csv_summary("grades.csv"))
