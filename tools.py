import csv
import os
import statistics


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


# Which function backs each supported stat name (stdev is the sample std).
STAT_FUNCTIONS = {
    "mean": statistics.mean,
    "median": statistics.median,
    "std": statistics.stdev,
    "min": min,
    "max": max,
}


def _is_number(text):
    """Return True if text can be converted to a float."""
    try:
        float(text)
        return True
    except ValueError:
        return False


def _numeric_column_names(header, data_rows):
    """Return the columns whose non-empty cells all parse as floats."""
    names = []
    for index, name in enumerate(header):
        cells = [
            row[index].strip()
            for row in data_rows
            if index < len(row) and row[index].strip()
        ]
        if cells and all(_is_number(cell) for cell in cells):
            names.append(name)
    return names


def calculate_stat(stat, column, file_name="grades.csv"):
    """Calculate one statistic (mean, median, std, min, max) for one CSV column.

    Returns {"stat", "column", "value", "rows_used"} on success, or an
    {"error": "..."} dict if the stat, column, file or data is unusable.
    """
    # Step 1: check the requested stat is one of the supported ones.
    stat_name = str(stat).strip().lower()
    if stat_name not in STAT_FUNCTIONS:
        valid = ", ".join(STAT_FUNCTIONS)
        return {"error": f"Unknown stat '{stat}'. Valid stats: {valid}"}

    # Step 2: check the file exists before trying to open it.
    if not os.path.exists(file_name):
        return {"error": f"File not found: {file_name}"}

    # Step 3: read every row, turning any read failure into an error dict.
    try:
        with open(file_name, newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        if not rows:
            raise ValueError("file is empty")
    except Exception as exc:
        return {"error": f"Could not read {file_name}: {exc}"}

    # Step 4: split the header from the data, dropping fully blank lines.
    header = [name.strip() for name in rows[0]]
    data_rows = [row for row in rows[1:] if any(cell.strip() for cell in row)]

    # Step 5: check the column exists and remember where it sits in each row.
    if column not in header:
        valid = ", ".join(header)
        return {"error": f"Unknown column '{column}'. Valid columns: {valid}"}
    column_index = header.index(column)

    # Step 6: collect the column's values, skipping empty cells and refusing text.
    values = []
    for row in data_rows:
        cell = row[column_index].strip() if column_index < len(row) else ""
        if not cell:
            continue
        if not _is_number(cell):
            numeric = ", ".join(_numeric_column_names(header, data_rows)) or "none"
            return {
                "error": (
                    f"Column '{column}' is not numeric: {cell!r} is not a number. "
                    f"Numeric columns: {numeric}"
                )
            }
        values.append(float(cell))

    # Step 7: make sure there are enough values for the requested stat.
    if not values:
        return {"error": f"Column '{column}' has no values to calculate from."}
    if stat_name == "std" and len(values) < 2:
        return {
            "error": f"'std' needs at least 2 values, but '{column}' has {len(values)}."
        }

    # Step 8: run the statistic on the values and round the answer.
    return {
        "stat": stat_name,
        "column": column,
        "value": round(STAT_FUNCTIONS[stat_name](values), 4),
        "rows_used": len(values),
    }


if __name__ == "__main__":
    # Small manual test: run this file directly to see the result.
    print(load_csv_summary("grades.csv"))

    # calculate_stat examples, including two error cases.
    print(calculate_stat("mean", "math"))
    print(calculate_stat("median", "science"))
    print(calculate_stat("std", "hours_studied"))
    print(calculate_stat("max", "student"))    # error: text column
    print(calculate_stat("average", "math"))   # error: unknown stat

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "load_csv_summary",
            "description": "Summarize a CSV file: return its column names, row count, and which columns are numeric. Use this first whenever the user asks what data is available, which columns exist, how many rows there are, or before analyzing the file, so you know the exact column names. The data file for this project is grades.csv.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "The name of the CSV file to read. Use \"grades.csv\" unless the user names a different file.",
                    }
                },
                "required": ["file_name"],
            },
        },
    },
]
