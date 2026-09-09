import { db, type SolveCount } from "./db";

// Pre-compile a query statement
const getLeaderboardStmt = db.prepare(`
  SELECT user_id, captcha_type, count 
  FROM solve_count 
  ORDER BY count DESC 
  LIMIT 10
`);

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

export function getLeaderboard(): SolveCount[] {
  // .all() returns an array. Casting it with 'as SolveCount[]' gives you full IDE autocompletion
  return getLeaderboardStmt.all() as SolveCount[];
}

console.log(getLeaderboard())