#!/usr/bin/env python3
"""
Seed script for NAV Scoring application.
Creates test data: admin, coach, members, pairings, and NAV routes.

Uses the new unified users table with role flags.
"""

import sys
from pathlib import Path
from app.database import Database
from app.auth import Auth

def seed_database(db_path: str = "data/navs.db"):
    """Populate database with test data."""
    
    print("🌱 Seeding NAV Scoring database...")
    print(f"   Database: {db_path}\n")
    
    db = Database(db_path)
    auth = Auth(db)
    
    with db.get_connection() as conn:
        # ===== ADMIN ACCOUNT =====
        print("👤 Creating admin account...")
        try:
            # Clear existing admin
            conn.execute('DELETE FROM users WHERE username = ?', ('admin',))
            admin_hash = auth.hash_password('admin123')
            conn.execute(
                'INSERT INTO users (username, password_hash, email, name, is_coach, is_admin, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('admin', admin_hash, 'admin@siu.edu', 'Main Administrator', 1, 1, 1)
            )
            print("   ✅ Admin created: username=admin, password=admin123\n")
        except Exception as e:
            print(f"   ⚠️  Admin creation failed: {e}\n")
        
        # ===== COACH ACCOUNT =====
        print("👤 Creating coach account...")
        try:
            conn.execute('DELETE FROM users WHERE username = ?', ('coach',))
            coach_hash = auth.hash_password('coach123')
            conn.execute(
                'INSERT INTO users (username, password_hash, email, name, is_coach, is_admin, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('coach', coach_hash, 'coach@siu.edu', 'Coach User', 1, 0, 1)
            )
            print("   ✅ Coach created: username=coach, password=coach123 (read-only access)\n")
        except Exception as e:
            print(f"   ⚠️  Coach creation failed: {e}\n")
        
        # ===== MEMBER (COMPETITOR) ACCOUNTS =====
        print("👥 Creating member accounts...")
        members_data = [
            # 6 members (will pair them as pilot+observer)
            ('pilot1', 'pass123', 'pilot1@siu.edu', 'Alex Johnson'),
            ('observer1', 'pass123', 'observer1@siu.edu', 'Taylor Brown'),
            ('pilot2', 'pass123', 'pilot2@siu.edu', 'Jordan Smith'),
            ('observer2', 'pass123', 'observer2@siu.edu', 'Morgan Davis'),
            ('pilot3', 'pass123', 'pilot3@siu.edu', 'Casey Martinez'),
            ('observer3', 'pass123', 'observer3@siu.edu', 'Riley Wilson'),
        ]
        
        try:
            # Clear existing members
            conn.execute('DELETE FROM users WHERE is_coach = 0')
            for username, password, email, name in members_data:
                password_hash = auth.hash_password(password)
                conn.execute(
                    'INSERT INTO users (username, password_hash, email, name, is_coach, is_admin, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (username, password_hash, email, name, 0, 0, 1)
                )
                print(f"   ✅ Member: {name} (username={username})")
            print(f"\n   📝 All members use password: pass123\n")
        except Exception as e:
            print(f"   ⚠️  Member creation failed: {e}\n")
        
        # ===== PENDING APPROVAL ACCOUNT (for testing) =====
        print("👤 Creating pending approval account...")
        try:
            conn.execute('DELETE FROM users WHERE username = ?', ('pending_user',))
            pending_hash = auth.hash_password('pass123')
            conn.execute(
                'INSERT INTO users (username, password_hash, email, name, is_coach, is_admin, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('pending_user', pending_hash, 'pending@siu.edu', 'Pending User', 0, 0, 0)
            )
            print("   ✅ Pending user created: username=pending_user (awaiting approval)\n")
        except Exception as e:
            print(f"   ⚠️  Pending user creation failed: {e}\n")
        
        # ===== CREATE TEST AIRPORT & NAV =====
        print("🗺️  Creating sample NAV routes...")
        try:
            # Create airport if needed
            cursor = conn.execute('SELECT id FROM airports WHERE code = ?', ('KMDH',))
            row = cursor.fetchone()
            if row:
                airport_id = row[0]
                print(f"   ℹ️  Using existing airport KMDH (id={airport_id})")
            else:
                cursor = conn.execute('INSERT INTO airports (code) VALUES (?)', ('KMDH',))
                airport_id = cursor.lastrowid
                print(f"   ✅ Created airport KMDH (id={airport_id})")
            
            # Check if NAVs exist
            existing_navs = conn.execute('SELECT COUNT(*) FROM navs').fetchone()[0]
            
            if existing_navs > 0:
                print(f"   ℹ️  Found {existing_navs} existing NAVs (keeping them)\n")
            else:
                # Create sample NAVs
                sample_navs = [
                    ('NAV-1', airport_id),
                    ('NAV-2', airport_id),
                    ('NAV-3', airport_id),
                ]
                
                for nav_name, airport in sample_navs:
                    conn.execute(
                        'INSERT INTO navs (name, airport_id) VALUES (?, ?)',
                        (nav_name, airport)
                    )
                    print(f"   ✅ Created NAV: {nav_name}")
                
                print(f"\n   📝 Note: NAVs need checkpoints/secrets added via coach admin\n")
        except Exception as e:
            print(f"   ⚠️  NAV creation failed: {e}\n")
        
        # ===== PAIRINGS =====
        print("🔗 Creating pairings...")
        try:
            conn.execute('DELETE FROM pairings')  # Clear existing
            
            # Get member IDs from unified users table (is_coach=0)
            members = conn.execute('SELECT id, username, name FROM users WHERE is_coach = 0 AND username NOT LIKE "pending%" ORDER BY id LIMIT 6').fetchall()
            
            if len(members) >= 6:
                # Pair: pilot1+observer1, pilot2+observer2, pilot3+observer3
                pairings = [
                    (members[0][0], members[1][0]),  # pilot1 + observer1
                    (members[2][0], members[3][0]),  # pilot2 + observer2
                    (members[4][0], members[5][0]),  # pilot3 + observer3
                ]
                
                for pilot_id, observer_id in pairings:
                    conn.execute(
                        'INSERT INTO pairings (pilot_id, safety_observer_id, is_active) VALUES (?, ?, 1)',
                        (pilot_id, observer_id)
                    )
                    pilot_name = next(m[2] for m in members if m[0] == pilot_id)
                    observer_name = next(m[2] for m in members if m[0] == observer_id)
                    print(f"   ✅ Paired: {pilot_name} (pilot) ← → {observer_name} (observer)")
                
                print()
            else:
                print(f"   ℹ️  Not enough members for pairings (found {len(members)}, need 6)\n")
        except Exception as e:
            print(f"   ⚠️  Pairing creation failed: {e}\n")
        
        # ===== SUMMARY =====
        print("=" * 60)
        print("✅ SEEDING COMPLETE!\n")
        print("🔐 LOGIN CREDENTIALS:")
        print("\n   ADMIN (Full Access):")
        print("      → http://localhost:8000/coach")
        print("      → username: admin")
        print("      → password: admin123\n")
        print("   COACH (Read-Only Access):")
        print("      → http://localhost:8000/coach")
        print("      → username: coach")
        print("      → password: coach123\n")
        print("   Team Members (Competitors):")
        print("      → http://localhost:8000/login")
        print("      → Pilots: pilot1, pilot2, pilot3")
        print("      → Observers: observer1, observer2, observer3")
        print("      → password: pass123 (all competitors)\n")
        print("   Pending Approval (for testing):")
        print("      → Username: pending_user")
        print("      → Password: pass123")
        print("      → Status: Awaiting admin approval\n")
        print("📊 DATABASE CONTENTS:")
        users_count = conn.execute('SELECT COUNT(*) FROM users WHERE is_approved = 1').fetchone()[0]
        pending_count = conn.execute('SELECT COUNT(*) FROM users WHERE is_approved = 0').fetchone()[0]
        pairings_count = conn.execute('SELECT COUNT(*) FROM pairings WHERE is_active = 1').fetchone()[0]
        navs_count = conn.execute('SELECT COUNT(*) FROM navs').fetchone()[0]
        print(f"   • {users_count} approved users")
        print(f"   • {pending_count} pending users")
        print(f"   • {pairings_count} active pairings")
        print(f"   • {navs_count} NAV routes")
        print("=" * 60)

if __name__ == '__main__':
    seed_database()
