"""One-off script to regenerate properties_db.py from the CSV."""
import csv
import os

csv_file = os.path.join(os.path.dirname(__file__), "Qterra_Dataset_with_URLs.csv")
out_file = os.path.join(os.path.dirname(__file__), "properties_db.py")

properties = []
with open(csv_file, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader, start=1):
        prop_type = row["PropertyType"].strip() or "Property"
        city = row["City"].strip()
        properties.append({
            "id": str(i),
            "type": prop_type,
            "address": row["Address"].strip(),
            "city": city,
            "availability": row["Availability"].strip(),
            "price": row["Price"].strip(),
            "beds": row["Beds"].strip(),
            "baths": row["Baths"].strip(),
            "url": row["URL"].strip(),
            "description": f"{prop_type} available for rent in {city}.",
        })

lines = ["PROPERTIES = ["]
for p in properties:
    lines.append("    {")
    for k, v in p.items():
        lines.append(f'        {k!r}: {v!r},')
    lines.append("    },")
lines.append("]")
lines.append("")
lines.append("")
lines.append("def search_properties(location: str = None, property_type: str = None):")
lines.append('    """Return up to 3 available (non-Leased) properties matching the filters."""')
lines.append("    results = [p for p in PROPERTIES if p.get('availability', '').lower() != 'leased']")
lines.append("    if location:")
lines.append("        results = [p for p in results if location.lower() in p['address'].lower()")
lines.append("                   or location.lower() in p['city'].lower()]")
lines.append("    if property_type:")
lines.append("        results = [p for p in results if property_type.lower() in p['type'].lower()]")
lines.append("    return results[-3:]  # Return 3 latest matches")
lines.append("")

with open(out_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Done! Wrote {len(properties)} properties to {out_file}")
