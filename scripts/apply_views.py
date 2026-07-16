import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "krickbot")

def main():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
    except Exception as e:
        print(f"Error connecting: {e}")
        return
    
    queries = [
        "DROP VIEW IF EXISTS `v_clean_player`",
        """CREATE VIEW `v_clean_player` AS
            SELECT 
                p.`PlayerId`,
                TRIM(p.`FullName`) AS `PlayerName`,
                TRIM(p.`ShortName`) AS `ShortName`,
                CASE WHEN p.`DOB` = '0000-00-00' OR p.`DOB` IS NULL THEN 'Not Available' ELSE DATE_FORMAT(p.`DOB`, '%Y-%m-%d') END AS `DateOfBirth`,
                TRIM(p.`BattingStyle`) AS `BattingStyle`,
                TRIM(p.`BowlingStyle`) AS `BowlingStyle`,
                TRIM(p.`PlayingRole`) AS `PlayingRole`,
                c.`ClubName`,
                ci.`CityName`,
                co.`CountryName`
            FROM 
                `player` p
            LEFT JOIN `club` c ON p.`ClubId` = c.`ClubId`
            LEFT JOIN `city` ci ON p.`CityId` = ci.`CityId`
            LEFT JOIN `country` co ON p.`CountryId` = co.`CountryCode`""",
            
        "DROP VIEW IF EXISTS `v_clean_club`",
        """CREATE VIEW `v_clean_club` AS
            SELECT
                c.`ClubId`,
                TRIM(c.`ClubName`) AS `ClubName`,
                TRIM(c.`President`) AS `President`,
                TRIM(c.`Coach`) AS `Coach`,
                a.`AssociationName`,
                ci.`CityName`,
                co.`CountryName`
            FROM
                `club` c
            LEFT JOIN `association` a ON c.`AssociationId` = a.`AssociationId`
            LEFT JOIN `city` ci ON c.`CityId` = ci.`CityId`
            LEFT JOIN `country` co ON c.`CountryId` = co.`CountryCode`""",
            
        "DROP VIEW IF EXISTS `v_player_career_batting`",
        """CREATE VIEW `v_player_career_batting` AS
            SELECT 
                `PlayerId`,
                COUNT(`Innings`) AS `TotalInnings`,
                SUM(`Runs`) AS `TotalRuns`,
                MAX(`Runs`) AS `HighestScore`,
                SUM(`BallsFaced`) AS `TotalBallsFaced`,
                SUM(`NotOut`) AS `TotalNotOuts`,
                ROUND(SUM(`Runs`) / NULLIF((COUNT(`Innings`) - SUM(`NotOut`)), 0), 2) AS `BattingAverage`,
                ROUND((SUM(`Runs`) / NULLIF(SUM(`BallsFaced`), 0)) * 100, 2) AS `StrikeRate`,
                SUM(CASE WHEN `Runs` >= 100 THEN 1 ELSE 0 END) AS `Hundreds`,
                SUM(CASE WHEN `Runs` >= 50 AND `Runs` < 100 THEN 1 ELSE 0 END) AS `Fifties`
            FROM `batting_detail`
            GROUP BY `PlayerId`""",
            
        "DROP VIEW IF EXISTS `v_player_career_bowling`",
        """CREATE VIEW `v_player_career_bowling` AS
            SELECT 
                `PlayerId`,
                COUNT(`Innings`) AS `TotalInningsBowled`,
                SUM(`Wickets`) AS `TotalWickets`,
                SUM(`Runs`) AS `TotalRunsConceded`,
                SUM(`Overs`) AS `TotalOversBowled`,
                ROUND(SUM(`Runs`) / NULLIF(SUM(`Wickets`), 0), 2) AS `BowlingAverage`,
                ROUND(SUM(`Runs`) / NULLIF(SUM(`Overs`), 0), 2) AS `EconomyRate`,
                SUM(CASE WHEN `Wickets` >= 5 THEN 1 ELSE 0 END) AS `FiveWicketHauls`
            FROM `bowling_detail`
            GROUP BY `PlayerId`""",
            
        "DROP VIEW IF EXISTS `v_player_recent_batting`",
        """CREATE VIEW `v_player_recent_batting` AS
            SELECT 
                `PlayerId`,
                SUM(`Runs`) AS `RecentRuns`,
                SUM(`BallsFaced`) AS `RecentBallsFaced`,
                ROUND(SUM(`Runs`) / NULLIF((COUNT(`Innings`) - SUM(`NotOut`)), 0), 2) AS `RecentAverage`,
                ROUND((SUM(`Runs`) / NULLIF(SUM(`BallsFaced`), 0)) * 100, 2) AS `RecentStrikeRate`
            FROM (
                SELECT 
                    `PlayerId`, 
                    `Runs`, 
                    `BallsFaced`, 
                    `NotOut`, 
                    `Innings`,
                    ROW_NUMBER() OVER(PARTITION BY `PlayerId` ORDER BY `MatchNo` DESC) as `rn`
                FROM `batting_detail`
            ) t
            WHERE t.`rn` <= 5
            GROUP BY `PlayerId`""",
            
        "DROP VIEW IF EXISTS `v_player_recent_bowling`",
        """CREATE VIEW `v_player_recent_bowling` AS
            SELECT 
                `PlayerId`,
                SUM(`Wickets`) AS `RecentWickets`,
                SUM(`Runs`) AS `RecentRunsConceded`,
                SUM(`Overs`) AS `RecentOversBowled`,
                ROUND(SUM(`Runs`) / NULLIF(SUM(`Wickets`), 0), 2) AS `RecentBowlingAverage`,
                ROUND(SUM(`Runs`) / NULLIF(SUM(`Overs`), 0), 2) AS `RecentEconomyRate`
            FROM (
                SELECT 
                    `PlayerId`, 
                    `Wickets`, 
                    `Runs`, 
                    `Overs`,
                    ROW_NUMBER() OVER(PARTITION BY `PlayerId` ORDER BY `MatchNo` DESC) as `rn`
                FROM `bowling_detail`
            ) t
            WHERE t.`rn` <= 5
            GROUP BY `PlayerId`""",
            
        "DROP VIEW IF EXISTS `v_batsman_vs_bowler_h2h`",
        """CREATE VIEW `v_batsman_vs_bowler_h2h` AS
            SELECT 
                `BatsmanId`,
                `BowlerId`,
                SUM(`Runs`) AS `RunsScored`,
                COUNT(`BallId`) AS `BallsFaced`,
                ROUND((SUM(`Runs`) / NULLIF(COUNT(`BallId`), 0)) * 100, 2) AS `StrikeRate`,
                SUM(`Wicket`) AS `TimesDismissed`
            FROM `ball_by_ball`
            GROUP BY `BatsmanId`, `BowlerId`"""
    ]
    
    with conn.cursor() as cursor:
        for q in queries:
            cursor.execute(q)
            
    conn.commit()
    conn.close()
    print("Successfully applied views to MariaDB instance.")

if __name__ == "__main__":
    main()
