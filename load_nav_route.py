#!/usr/bin/env python3
"""Load NAV route from nav_route.txt"""

import sys
sys.path.insert(0, '/app')
from app.database import Database

db = Database('/app/data/navs.db')

# Get or create KMDH airport
with db.get_connection() as conn:
    cursor = conn.execute('SELECT id FROM airports WHERE code = ?', ('KMDH',))
    airport_row = cursor.fetchone()
    if airport_row:
        airport_id = airport_row['id']
    else:
        cursor = conn.execute('INSERT INTO airports (code) VALUES (?)', ('KMDH',))
        airport_id = cursor.lastrowid
    
    print(f'Using airport KMDH (ID: {airport_id})')
    
    # Delete existing start gates for KMDH
    conn.execute('DELETE FROM start_gates WHERE airport_id = ?', (airport_id,))
    
    # Add start gates from nav_route.txt
    start_gates = [
        ('18L/36R and 6/24', 37.7804409, -89.2482244),
        ('18R/36L and 6/24', 37.7756208, -89.2585710)
    ]
    
    for name, lat, lon in start_gates:
        conn.execute(
            'INSERT INTO start_gates (airport_id, name, lat, lon) VALUES (?, ?, ?, ?)',
            (airport_id, name, lat, lon)
        )
        print(f'Added start gate: {name}')
    
    # Check for existing MDH 20
    cursor = conn.execute('SELECT id FROM navs WHERE name = ?', ('MDH 20',))
    existing = cursor.fetchone()
    if existing:
        nav_id = existing['id']
        print(f'Found existing MDH 20 (ID: {nav_id}), deleting checkpoints...')
        conn.execute('DELETE FROM checkpoints WHERE nav_id = ?', (nav_id,))
    else:
        cursor = conn.execute('INSERT INTO navs (name, airport_id) VALUES (?, ?)', ('MDH 20', airport_id))
        nav_id = cursor.lastrowid
        print(f'Created MDH 20 NAV (ID: {nav_id})')
    
    # Add checkpoints from nav_route.txt (fixing the typo in checkpoint 3)
    checkpoints = [
        (1, 'Baseball Field', 37.4719349, -88.9773922),
        (2, 'Railroad Crossing', 37.3431168, -88.7181987),
        (3, 'Covered Boat Parking', 37.3708942, -88.4822528),
        (4, 'Long Rectangle Pond', 37.6803795, -88.642212),
        (5, 'Truck Stop', 37.6193232, -88.9861208)
    ]
    
    for seq, name, lat, lon in checkpoints:
        conn.execute(
            'INSERT INTO checkpoints (nav_id, sequence, name, lat, lon) VALUES (?, ?, ?, ?, ?)',
            (nav_id, seq, name, lat, lon)
        )
        print(f'  {seq}. {name} ({lat}, {lon})')
    
    conn.commit()
    print('\n✅ MDH 20 NAV route loaded successfully with all 5 checkpoints!')

# Verify
navs = db.list_navs()
mdh20 = None
for nav in navs:
    if nav['name'] == 'MDH 20':
        mdh20 = db.get_nav(nav['id'])
        break

if mdh20:
    print(f'\n✓ Verification: NAV Route "{mdh20["name"]}" has {len(mdh20["checkpoints"])} checkpoints')
