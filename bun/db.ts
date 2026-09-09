// import { Database } from "bun:sqlite";

// const db = new Database(":memory:");
// const query = db.query("select 'Hello world' as message;");
// query.get();

// bun x sqlite3 database.db "INSERT INTO solve_event (id, user_id, captcha_type, solved_at) SELECT id, user_id, captcha_type, solved_at FROM solveevent; INSERT INTO solve_count (user_id, captcha_type, count) SELECT user_id, captcha_type, count FROM solvecount;"

import { Database } from "bun:sqlite";

export const db = new Database("database.db");

// setup foreign keys so we can link between things
db.run("PRAGMA foreign_keys = ON;");

// perf, WAL mode and stuff
db.run("PRAGMA journal_mode=WAL;");
db.run("PRAGMA synchronous=NORMAL;");
db.run("PRAGMA busy_timeout=5000;");


// makey tables
db.run(`
  CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE
  );
  
  CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);

  CREATE TABLE IF NOT EXISTS solve_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    captcha_type TEXT NOT NULL,
    solved_at INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(id)
  );

  CREATE INDEX IF NOT EXISTS idx_solve_event_solved_at ON solve_event(solved_at);

  CREATE TABLE IF NOT EXISTS solve_count (
    user_id INTEGER NOT NULL,
    captcha_type TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, captcha_type),
    FOREIGN KEY(user_id) REFERENCES user(id)
  );

  CREATE TABLE IF NOT EXISTS solve_bucket (
    bucket_time INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    captcha_type TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (bucket_time, user_id, captcha_type),
    FOREIGN KEY(user_id) REFERENCES user(id)
  );
`);

// warning: i do not undertand ts types properly.

// ok this isn't too bad i hope, update if incorrect
export interface User { id?: number; username: string; }
export interface SolveEvent { id?: number; user_id: number; captcha_type: string; solved_at: number; }
export interface SolveCount {
  user_id: number;
  captcha_type: string;
  count: number;
}
export interface SolveBucket {
  bucket_time: number;
  user_id: number;
  captcha_type: string;
  count: number;
}

// i didn't even know upsert was a word, but i'll stick with that, thanks gemini
// changed it to bump lol
// Pre-compile statements for speed
const insertEventStmt = db.prepare(`
  INSERT INTO solve_event (user_id, captcha_type, solved_at) 
  VALUES ($user_id, $captcha_type, $solved_at)
`);

const bumpCountStmt = db.prepare(`
  INSERT INTO solve_count (user_id, captcha_type, count)
  VALUES ($user_id, $captcha_type, 1)
  ON CONFLICT(user_id, captcha_type) DO UPDATE SET count = count + 1
`);

const bumpBucketStmt = db.prepare(`
  INSERT INTO solve_bucket (bucket_time, user_id, captcha_type, count)
  VALUES ($bucket_time, $user_id, $captcha_type, 1)
  ON CONFLICT(bucket_time, user_id, captcha_type) DO UPDATE SET count = count + 1
`);

/**
 * Records a single solve event and updates cache rollups in a single atomic transaction.
 * TODO: look into the single thread that takes writelock for sqlite, + queue
 * see solve_writer.py
 */
export const recordSolve = db.transaction((userId: number, captchaType: string) => {
  const now = Math.floor(Date.now() / 1000); // Unix timestamp
  const bucketTime = now - (now % 300);      // 5-minute bucket grouping (300 seconds)

  // 1. Append-only history log - SolveEvent
  insertEventStmt.run({
    $user_id: userId,
    $captcha_type: captchaType,
    $solved_at: now
  });

  // 2. Increment running tally for leaderboard - SolveCount
  bumpCountStmt.run({
    $user_id: userId,
    $captcha_type: captchaType
  });

  // 3. Increment 5-minute rollup for graphs SolveBucket
  bumpBucketStmt.run({
    $bucket_time: bucketTime,
    $user_id: userId,
    $captcha_type: captchaType
  });
});
