import json

scraped_data = [
  {"address": "1105-1 Jarvis St, Hamilton, Ontario L8R 3J2", "url": "https://www.qterrapropertymanagement.com/properties/1105-1-jarvis-st%2C-hamilton%2C-ontario-l8r-3j2"},
  {"address": "2-133 Marchington Cir, Scarborough, Ontario M1R 3M9", "url": "https://www.qterrapropertymanagement.com/properties/2-133-marchington-cir%2C-scarborough%2C-ontario-m1r-3m9"},
  {"address": "N701-35 Rolling Mills Road, Toronto, Ontario M5A 0V6", "url": "https://www.qterrapropertymanagement.com/properties/n701-35-rolling-mills-road%2C-toronto%2C-ontario-m5a-0v6"},
  {"address": "2-11 Northern Breeze Cres, Whitby, Ontario L1R 0P4", "url": "https://www.qterrapropertymanagement.com/properties/2-11-northern-breeze-cres%2C-whitby%2C-ontario-l1r-0p4"},
  {"address": "1-484 Main St E, Hamilton, Ontario L8N 1K6", "url": "https://www.qterrapropertymanagement.com/properties/1-484-main-st-e%2C-hamilton%2C-ontario-l8n-1k6"},
  {"address": "3-142 Brock St, Brockville, Ontario K6V 4G4", "url": "https://www.qterrapropertymanagement.com/properties/3-142-brock-st%2C-brockville%2C-ontario-k6v-4g4"},
  {"address": "2-14 Cranston Manor Ct, Scarborough, Ontario M1J 3M6", "url": "https://www.qterrapropertymanagement.com/properties/2-14-cranston-manor-ct%2C-scarborough%2C-ontario-m1j-3m6"},
  {"address": "1-142 Brock St, Brockville, Ontario K6V 4G4", "url": "https://www.qterrapropertymanagement.com/properties/1-142-brock-st%2C-brockville%2C-ontario-k6v-4g4"},
  {"address": "3-234 King St W, Hamilton, Ontario L8P 1A9", "url": "https://www.qterrapropertymanagement.com/properties/3-234-king-st-w%2C-hamilton%2C-ontario-l8p-1a9"},
  {"address": "5-1 Bond Crescent, Richmond Hill, Ontario L4E 1J4", "url": "https://www.qterrapropertymanagement.com/properties/5-1-bond-crescent%2C-richmond-hill%2C-ontario-l4e-1j4"},
  {"address": "3-484 Main St E, Hamilton, Ontario L8N 1K6", "url": "https://www.qterrapropertymanagement.com/properties/3-484-main-st-e%2C-hamilton%2C-ontario-l8n-1k6"},
  {"address": "2-4377 Violet Rd, Mississauga, Ontario L5V 1J8", "url": "https://www.qterrapropertymanagement.com/properties/2-4377-violet-rd%2C-mississauga%2C-ontario-l5v-1j8"},
  {"address": "2-2409 Bankside Dr, Mississauga, Ontario L5M 6E6", "url": "https://www.qterrapropertymanagement.com/properties/2-2409-bankside-dr%2C-mississauga%2C-ontario-l5m-6e6"},
  {"address": "406-10 Morrison St, Toronto, Ontario M5V 2T8", "url": "https://www.qterrapropertymanagement.com/properties/406-10-morrison-st%2C-toronto%2C-ontario-m5v-2t8"},
  {"address": "612-1440 Clarriage Ct, Milton, Ontario L9T 2X5", "url": "https://www.qterrapropertymanagement.com/properties/612-1440-clarriage-ct%2C-milton%2C-ontario-l9T-2x5"},
  {"address": "98 Canter Blvd, Nepean, Ontario K2G 2M7", "url": "https://www.qterrapropertymanagement.com/properties/98-canter-blvd%2C-nepean%2C-ontario-k2g-2m7"},
  {"address": "1-60 Normandy Crescent, Richmond Hill, Ontario L4C 8L7", "url": "https://www.qterrapropertymanagement.com/properties/1-60-normandy-crescent%2C-richmond-hill%2C-ontario-l4c-8l7"},
  {"address": "111-1103 Jalna Blvd, London, Ontario N6E 2W8", "url": "https://www.qterrapropertymanagement.com/properties/111-1103-jalna-blvd%2C-london%2C-ontario-n6e-2w8"},
  {"address": "7-1370 Killarney Beach Rd, Innisfil, Ontario L0L 1W0", "url": "https://www.qterrapropertymanagement.com/properties/7-1370-killarney-beach-rd%2C-innisfil%2C-ontario-l0l-1w0"},
  {"address": "2-2443 Pagé Rd, Orleans, Ontario K1W 1H2", "url": "https://www.qterrapropertymanagement.com/properties/2-2443-page-rd%2C-orleans%2C-ontario-k1w-1h2"},
  {"address": "247-1075 Douglas McCurdy Cmn, Mississauga, Ontario L5G 0C6", "url": "https://www.qterrapropertymanagement.com/properties/247-1075-douglas-mccurdy-cmn%2C-mississauga%2C-ontario-l5g-0c6"},
  {"address": "2-142 Brock St, Brockville, Ontario K6V 4G4", "url": "https://www.qterrapropertymanagement.com/properties/2-142-brock-st%2C-brockville%2C-ontario-k6v-4g4"},
  {"address": "2-423 Mississauga Vly Blvd, Mississauga, Ontario L5A 1Y9", "url": "https://www.qterrapropertymanagement.com/properties/2-423-mississauga-vly-blvd%2C-mississauga%2C-ontario-l5a-1y9"},
  {"address": "103-30 Samuel Wood Way, Etobicoke, Ontario M9B 0C9", "url": "https://www.qterrapropertymanagement.com/properties/103-30-samuel-wood-way%2C-etobicoke%2C-ontario-m9b-0c9"}
]

import properties_db

url_map = {item['address']: item['url'] for item in scraped_data}

new_properties = []
for p in properties_db.PROPERTIES:
    if p['address'] in url_map:
        p['url'] = url_map[p['address']]
    new_properties.append(p)

with open('properties_db.py', 'w', encoding='utf-8') as f:
    f.write('PROPERTIES = [\n')
    for i, p in enumerate(new_properties):
        f.write('    {\n')
        f.write(f'        "id": "{p["id"]}",\n')
        f.write(f'        "type": "{p["type"]}",\n')
        f.write(f'        "address": "{p["address"]}",\n')
        f.write(f'        "description": "{p["description"]}"')
        if "url" in p:
            f.write(f',\n        "url": "{p["url"]}"\n')
        else:
            f.write('\n')
        f.write('    }')
        if i < len(new_properties) - 1:
            f.write(',\n')
        else:
            f.write('\n')
    f.write(']\n\n')
    f.write('def search_properties(location: str = None, property_type: str = None):\n')
    f.write('    results = PROPERTIES\n')
    f.write('    if location:\n')
    f.write('        results = [p for p in results if location.lower() in p["address"].lower()]\n')
    f.write('    if property_type:\n')
    f.write('        results = [p for p in results if property_type.lower() in p["type"].lower()]\n')
    f.write('    \n')
    f.write('    return results[-2:] # Return 2 latest matches\n')

print("Update complete")
