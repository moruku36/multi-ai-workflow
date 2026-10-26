def process_records(items):
    results = []
    for item in items:
        if item.get("active"):
            results.append(item["value"] * 2)
    return results


def calculate_total(values):
    total = 0
    for v in values:
        total += v
    return total
