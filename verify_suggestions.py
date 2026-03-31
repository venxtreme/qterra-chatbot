import properties_db

def test_suggestion_count():
    print("Testing property suggestion count...")
    # Mississauga basements - should have many matches in the DB
    results = properties_db.search_properties(location="Mississauga", property_type="Basement")
    print(f"Matches for 'Basement in Mississauga': {len(results)}")
    for p in results:
        print(f" - ID: {p['id']}, Address: {p['address']}")
    
    assert len(results) <= 2, f"Expected at most 2 results, got {len(results)}"
    
    # The DB has Mississauga matches: 10, 17, 18 (looking at properties_db.py)
    # results[-2:] should give 17 and 18 if they are the latest.
    results_all = properties_db.search_properties(location="Mississauga")
    print(f"Matches for 'Mississauga' (all types): {len(results_all)}")
    for p in results_all:
        print(f" - ID: {p['id']}, Type: {p['type']}, Address: {p['address']}")
    
    assert len(results_all) == 2, f"Expected 2 results, got {len(results_all)}"
    ids = [int(p['id']) for p in results_all]
    print(f"IDs: {ids}")
    assert ids == [17, 18], f"Expected IDs [17, 18] (latest 2), got {ids}"

    print("Success!")

if __name__ == "__main__":
    test_suggestion_count()
