import { db, type SolveCount } from "./db";



/*
 * The get leaderboard code is errorneous rn
{
  "ts": 1788942250.3959675,
  "data": [
    {
      "username": "@jmw",
      "total": 15771996,
      "by_type": {
        "cf-turnstile": 1167484,
        "recaptcha-v2": 17609,
        "vercel-botid-basic": 586,
        "cap-default": 14586316,
        "hcaptcha": 1
      }
    },
    {
      "username": "@devansh",
      "total": 13912196,
      "by_type": {
        "cf-turnstile": 2153069,
        "cap-default": 11756303,
        "vercel-botid-basic": 2824
      }
    },
    {
      "username": "https://meowing.au",
      "total": 6133665,
      "by_type": {
        "cf-turnstile": 25840,
        "vercel-botid-basic": 357279,
        "hcaptcha": 22,
        "cap-default": 5750524
      }
    },
    {
      "username": "krn",
      "total": 1259237,
      "by_type": {
        "cap-default": 1024654,
        "cf-turnstile": 234560,
        "vercel-botid-basic": 23
      }
    },
    {
      "username": "coolton",
      "total": 463588,
      "by_type": {
        "cf-turnstile": 405185,
        "vercel-botid-basic": 978,
        "cap-default": 57424,
        "hcaptcha": 1
      }
    },
    ....
      "total_solved": 38385719,
  "cache_age": 26
  should be the proper format
  cache ttl is 30s afaik

*/

// FIX FIX FIX
// export function getLeaderboard(): SolveCount[] {
//   // .all() returns an array. Casting it with 'as SolveCount[]' gives you full IDE autocompletion
//   return getLeaderboardStmt.all() as SolveCount[];
// }

// console.log(getLeaderboard())

import { db } from "./db";

// Types mapping directly to your target JSON structure
interface LeaderboardUser {
  username: string;
  total: number;
  by_type: Record<string, number>;
}

interface LeaderboardPayload {
  ts: number;
  data: LeaderboardUser[];
  total_solved: number;
  cache_age: number;
}

// Raw row output mapping from SQLite
interface LeaderboardRow {
  username: string;
  total: number;
  by_type_json: string; // Packed SQLite JSON string
}

// 1. Compiled high-performance queries
const getLeaderboardDataStmt = db.prepare(`
  SELECT 
    u.username,
    SUM(sc.count) as total,
    json_group_object(sc.captcha_type, sc.count) as by_type_json
  FROM solve_count sc
  JOIN user u ON sc.user_id = u.id
  GROUP BY sc.user_id
  ORDER BY total DESC
`);

const getTotalSolvedStmt = db.prepare(`
  SELECT SUM(count) as global_total FROM solve_count
`);

// 2. Cache variables (30-second TTL)
let cachedPayload: LeaderboardPayload | null = null;
let lastCacheFetchTime = 0;
const CACHE_TTL_MS = 30 * 1000;

/**
 * Fetches the nested leaderboard data, tracks structural aggregates,
 * and maintains a 30-second in-memory cache lifecycle.
 */
export function getLeaderboard(): LeaderboardPayload {
  const nowMs = Date.now();
  const nowSec = nowMs / 1000;

  // Serve from cache if it is still young
  if (cachedPayload && (nowMs - lastCacheFetchTime) < CACHE_TTL_MS) {
    return {
      ...cachedPayload,
      cache_age: Math.floor((nowMs - lastCacheFetchTime) / 1000)
    };
  }

  // Cache is stale or missing; rebuild it from the DB - yes sync query slows down one request i hope??
  const rawRows = getLeaderboardDataStmt.all() as LeaderboardRow[];
  const totalSolvedRow = getTotalSolvedStmt.get() as { global_total: number | null };
  const globalTotal = totalSolvedRow?.global_total ?? 0;

  // Map SQLite JSON strings back to typed JavaScript objects
  const structuredData: LeaderboardUser[] = rawRows.map(row => ({
    username: row.username,
    total: row.total,
    by_type: JSON.parse(row.by_type_json)
  }));

  // Save state to cache
  cachedPayload = {
    ts: nowSec,
    data: structuredData,
    total_solved: globalTotal,
    cache_age: 0
  };
  lastCacheFetchTime = nowMs;

  return cachedPayload;
}


// console.log(JSON.stringify(getLeaderboard(), null, 2));