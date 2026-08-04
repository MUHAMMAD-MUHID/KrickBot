"""Quick investigation script for the two failing questions."""
from sqlalchemy import text
from app.database import engine

with engine.connect() as c:
    # 1. Check PSL tournaments
    print("=== PSL / Pakistan Super League Tournaments ===")
    rows = c.execute(text(
        "SELECT TournamentId, Name, Season, Winner FROM tournament "
        "WHERE Name LIKE '%PSL%' OR Name LIKE '%Pakistan Super%' OR Name LIKE '%Super League%' "
        "ORDER BY Season DESC LIMIT 10"
    )).fetchall()
    if rows:
        for r in rows:
            print(r)
    else:
        print("No PSL tournaments found. Checking all tournament names...")
        rows2 = c.execute(text("SELECT DISTINCT Name FROM tournament LIMIT 30")).fetchall()
        for r in rows2:
            print(f"  - {r[0]}")

    # 2. Check grounds in Pakistan via JOINs
    print("\n=== Grounds in Pakistan (via city→country JOIN) ===")
    rows = c.execute(text(
        "SELECT COUNT(*) as cnt FROM ground g "
        "JOIN city ci ON g.CityId = ci.CityId "
        "JOIN country co ON ci.CountryCode = co.CountryCode "
        "WHERE co.CountryName LIKE '%Pakistan%'"
    )).fetchone()
    print(f"Grounds in Pakistan: {rows[0]}")

    # 3. Check ground table directly for CountryCode
    print("\n=== Ground table has CountryCode column ===")
    rows = c.execute(text(
        "SELECT COUNT(*) as cnt FROM ground WHERE CountryCode IS NOT NULL"
    )).fetchone()
    print(f"Grounds with CountryCode set: {rows[0]}")

    # 4. Check if matches have CountryName
    print("\n=== matches.CountryName sample ===")
    rows = c.execute(text(
        "SELECT DISTINCT CountryName FROM matches WHERE CountryName IS NOT NULL LIMIT 10"
    )).fetchall()
    for r in rows:
        print(f"  - {r[0]}")
