"""Test the SQL parser to see what data is being extracted"""

import re

BACKUP_SQL_FILE = r"c:\Users\wal_g\Downloads\backup_sma87327-20261022\backup_sma87327-20261022.sql"


def parse_insert_values(insert_statement):
    """Extract values from INSERT INTO statement"""
    # Find the VALUES clause
    values_match = re.search(r"VALUES\s+(.+);", insert_statement, re.DOTALL | re.IGNORECASE)
    if not values_match:
        return []

    values_str = values_match.group(1)
    rows = []

    # Split by '),(' to get individual rows
    # Handle the first '(' and last ')'
    values_str = values_str.strip()
    if values_str.startswith("("):
        values_str = values_str[1:]
    if values_str.endswith(")"):
        values_str = values_str[:-1]

    # Split on '),(' pattern
    row_strings = re.split(r"\),\s*\(", values_str)

    for row_str in row_strings[:5]:  # Just first 5 rows for testing
        # Parse individual values - simpler approach
        values = []
        current_value = ""
        in_string = False
        i = 0

        while i < len(row_str):
            char = row_str[i]

            # Handle escaped characters
            if char == "\\" and i + 1 < len(row_str):
                current_value += row_str[i + 1]
                i += 2
                continue

            # Handle string delimiters
            if char == "'":
                if in_string:
                    # End of string - add value
                    values.append(current_value)
                    current_value = ""
                    in_string = False
                    # Skip to next comma
                    i += 1
                    while i < len(row_str) and row_str[i] != ",":
                        i += 1
                    i += 1
                    continue
                else:
                    # Start of string
                    in_string = True
                    i += 1
                    continue

            # Handle commas outside strings
            if char == "," and not in_string:
                # Value separator for non-string values
                val = current_value.strip()
                if val == "NULL" or val == "":
                    values.append(None)
                else:
                    values.append(val)
                current_value = ""
                i += 1
                continue

            # Add character to current value
            if in_string or char not in (" ", "\t", "\n", "\r"):
                current_value += char

            i += 1

        # Add last value
        val = current_value.strip()
        if val == "NULL" or val == "":
            values.append(None)
        else:
            values.append(val)

        rows.append(values)

    return rows


# Read a small portion and test
print("Testing SQL parser...")
print("=" * 60)

with open(BACKUP_SQL_FILE, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Find student INSERT statement
match = re.search(r"INSERT INTO `student` VALUES(.+?);", content, re.DOTALL)
if match:
    insert_stmt = "INSERT INTO `student` VALUES" + match.group(1) + ";"
    rows = parse_insert_values(insert_stmt)

    print(f"Found {len(rows)} student rows")
    print("\nFirst student row:")
    if rows:
        row = rows[0]
        print(f"Total fields: {len(row)}")
        print(f"Field 0 (studid): {row[0] if len(row) > 0 else 'N/A'}")
        print(f"Field 1 (lastname): {row[1] if len(row) > 1 else 'N/A'}")
        print(f"Field 2 (firstname): {row[2] if len(row) > 2 else 'N/A'}")
        print(f"Field 8 (studnum): {row[8] if len(row) > 8 else 'N/A'}")
        print(f"Field 9 (grade): {row[9] if len(row) > 9 else 'N/A'}")
        print(f"Field 10 (homeroom): {row[10] if len(row) > 10 else 'N/A'}")
        print(f"Field 11 (sex): {row[11] if len(row) > 11 else 'N/A'}")

        print("\nAll fields 0-50:")
        for i in range(min(51, len(row))):
            val = row[i]
            if val:  # Only show non-empty fields
                print(f"  [{i}]: {val}")
else:
    print("Could not find student INSERT statement")
