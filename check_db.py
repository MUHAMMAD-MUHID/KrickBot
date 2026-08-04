from app.query_pipeline.text_to_sql import execute_sql

r1 = execute_sql("SELECT MatchNo, Season, WinnerName, RunnerupName, Type, Format FROM matches LIMIT 20")
print("All matches:")
for r in r1:
    print(r)

r2 = execute_sql("SELECT * FROM tournament LIMIT 10")
print("\nTournaments:", r2)

r3 = execute_sql("SELECT Season, COUNT(*) as cnt, MAX(Dated) as latest FROM matches GROUP BY Season ORDER BY Season DESC LIMIT 10")
print("\nMatches by season:", r3)
