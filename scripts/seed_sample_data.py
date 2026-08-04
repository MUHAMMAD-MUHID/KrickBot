"""
Seed script: populates the MariaDB database with rich sample cricket data.
Inserts teams, players, matches, batting stats, and bowling stats.
"""

from sqlalchemy import text
from app.database import engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

def seed_database():
    logger.info("Seeding sample cricket data into MariaDB...")
    with engine.begin() as conn:
        # 1. Teams
        conn.execute(text("""
            INSERT IGNORE INTO team (TeamId, TeamName, ShortName, Level, Season) VALUES
            (1, 'Pakistan', 'PAK', 'International', '2024'),
            (2, 'India', 'IND', 'International', '2024'),
            (3, 'Australia', 'AUS', 'International', '2024'),
            (4, 'Peshawar Zalmi', 'PZ', 'League', '2024'),
            (5, 'Lahore Qalandars', 'LQ', 'League', '2024')
        """))

        # 2. Players
        conn.execute(text("""
            INSERT IGNORE INTO player (PlayerId, FullName, BattingStyle, BowlingStyle, PlayingRole) VALUES
            (101, 'Babar Azam', 'Right-hand bat', 'Right-arm offbreak', 'Batsman'),
            (102, 'Mohammad Rizwan', 'Right-hand bat', 'None', 'Wicketkeeper Batsman'),
            (103, 'Shaheen Afridi', 'Left-hand bat', 'Left-arm fast', 'Bowler'),
            (104, 'Haris Rauf', 'Right-hand bat', 'Right-arm fast', 'Bowler'),
            (105, 'Shadab Khan', 'Right-hand bat', 'Right-arm legbreak', 'All-Rounder'),
            (106, 'Virat Kohli', 'Right-hand bat', 'Right-arm medium', 'Batsman'),
            (107, 'Rohit Sharma', 'Right-hand bat', 'Right-arm offbreak', 'Batsman'),
            (108, 'Jasprit Bumrah', 'Right-hand bat', 'Right-arm fast', 'Bowler')
        """))

        # 3. Batting Stats
        conn.execute(text("""
            INSERT IGNORE INTO batting_stats 
            (PlayerId, Season, Stage, Format, Matches, Inn, NotOut, Runs, HS, Average, BF, SR, Hundreds, Fifties, Zeros, PlayerName) VALUES
            (101, '2024', 'Group', 'T20I', 20, 20, 3, 750, 105, 44.12, 540, 138.88, 1, 6, 0, 'Babar Azam'),
            (101, '2023', 'Group', 'ODI', 25, 25, 4, 1100, 151, 52.38, 1220, 90.16, 3, 8, 1, 'Babar Azam'),
            (102, '2024', 'Group', 'T20I', 18, 18, 5, 680, 89, 52.30, 510, 133.33, 0, 7, 0, 'Mohammad Rizwan'),
            (106, '2024', 'Group', 'T20I', 15, 15, 4, 620, 92, 56.36, 440, 140.90, 0, 6, 0, 'Virat Kohli'),
            (107, '2024', 'Group', 'T20I', 16, 16, 2, 580, 121, 41.42, 390, 148.71, 2, 4, 1, 'Rohit Sharma'),
            (105, '2024', 'Group', 'T20I', 14, 12, 3, 240, 48, 26.66, 170, 141.17, 0, 0, 0, 'Shadab Khan')
        """))

        # 4. Bowling Stats
        conn.execute(text("""
            INSERT IGNORE INTO bowling_stats
            (PlayerId, Season, Stage, Format, Matches, Inn, Balls, Runs, Wickets, BBI, Average, Economy, StrikeRate, Fourfor, Fivefor, PlayerName) VALUES
            (103, '2024', 'Group', 'T20I', 18, 18, 420, 525, 28, '4/22', 18.75, 7.50, 15.00, 2, 0, 'Shaheen Afridi'),
            (104, '2024', 'Group', 'T20I', 16, 16, 360, 480, 24, '4/18', 20.00, 8.00, 15.00, 1, 0, 'Haris Rauf'),
            (108, '2024', 'Group', 'T20I', 15, 15, 360, 390, 30, '4/14', 13.00, 6.50, 12.00, 3, 1, 'Jasprit Bumrah'),
            (105, '2024', 'Group', 'T20I', 14, 14, 312, 400, 18, '3/20', 22.22, 7.69, 17.33, 0, 0, 'Shadab Khan')
        """))

        # 5. Matches
        conn.execute(text("""
            INSERT IGNORE INTO matches
            (MatchNo, Season, Dated, Winner, RunnerUP, WinnerName, RunnerupName, Team1, Team2, Team1Name, Team2Name, ResultDetail, ResultType, Format, Type) VALUES
            (1001, '2024', '2024-06-09 14:30:00', 2, 1, 'India', 'Pakistan', 1, 2, 'Pakistan', 'India', 'Won by 6 runs', 'WinLoss', 'T20I', 'League'),
            (1002, '2024', '2024-06-11 18:00:00', 1, 3, 'Pakistan', 'Australia', 1, 3, 'Pakistan', 'Australia', 'Won by 5 wickets', 'WinLoss', 'T20I', 'League'),
            (1003, '2024', '2024-03-18 20:00:00', 5, 4, 'Lahore Qalandars', 'Peshawar Zalmi', 4, 5, 'Peshawar Zalmi', 'Lahore Qalandars', 'Won by 12 runs', 'WinLoss', 'T20', 'League')
        """))

        # 6. Batting Detail
        conn.execute(text("""
            INSERT IGNORE INTO batting_detail
            (MatchNo, Innings, PlayerId, Runs, BallsFaced, Fours, Sixes, NotOut, HowOut, BatsmanName, TeamId, TeamName, Position) VALUES
            (1001, 1, 106, 31, 26, 3, 0, 0, 'Caught', 'Virat Kohli', 2, 'India', 3),
            (1001, 1, 107, 13, 12, 1, 1, 0, 'LBW', 'Rohit Sharma', 2, 'India', 1),
            (1001, 2, 101, 44, 43, 2, 0, 0, 'Caught', 'Babar Azam', 1, 'Pakistan', 1),
            (1001, 2, 102, 31, 31, 2, 1, 0, 'Bowled', 'Mohammad Rizwan', 1, 'Pakistan', 2),
            (1002, 1, 101, 75, 47, 8, 2, 1, 'Not Out', 'Babar Azam', 1, 'Pakistan', 1)
        """))

        # 7. Bowling Detail
        conn.execute(text("""
            INSERT IGNORE INTO bowling_detail
            (MatchNo, Innings, PlayerId, Overs, Maiden, Runs, Wickets, BowlerName, TeamId, TeamName) VALUES
            (1001, 1, 103, 4.0, 0, 31, 3, 'Shaheen Afridi', 1, 'Pakistan'),
            (1001, 1, 104, 4.0, 0, 28, 3, 'Haris Rauf', 1, 'Pakistan'),
            (1001, 2, 108, 4.0, 0, 14, 3, 'Jasprit Bumrah', 2, 'India')
        """))

    logger.info("[OK] Sample cricket data seeded successfully!")

if __name__ == "__main__":
    seed_database()
