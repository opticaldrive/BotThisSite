import { getLeaderboard } from "./leaderboard";
console.log("Hello via Bunsaa!");
const server = Bun.serve({
  // `routes` requires Bun v1.2.3+
  routes: {
    // Static routes
    "/*": { dir: "./static" },

    "/api/status": new Response("OK"),
    "/health": new Response("ok"),
    // DONE leaderboard and totals
    "/api/leaderboard": req => {
      const leaderboardData = getLeaderboard();
      return Response.json(leaderboardData);
    },
    "/api/total_captchas": req => {
      const leaderboardData = getLeaderboard();
      const total = String(leaderboardData.total_solved); 
      return new Response(total);
    },
    "/api/total_captchas_json": req => {
      const leaderboardData = getLeaderboard();
      return Response.json({ total_captchas: leaderboardData.total_solved });
    },

  // INCOMPLETE graphs
    // "/api/graphs/solves" 
    // "/api/graphs/user-solves" 
    // "/api/graphs/user-scores" 
  // get the other routes
  // INCOMPLETE challenges
    "/captchas/verify/:slug":  {
      POST: async req => {
         // verify logic here
      },
    },  
    // "/captchas/:slug": {
    //   // how does one autogenerate it idk
    // },
    // example routes leave
    // Dynamic route
    "/users/:id": req => {
      return new Response(`Hello User ${req.params.id}!`);
    },
    
    // Per-HTTP method handlers
    "/api/posts": {
      GET: () => new Response("List posts"),
      POST: async req => {
        const body = await req.json();
        return Response.json({ created: true, ...body });
      },
    },

    // Wildcard route for all routes that start with "/api/" and aren't otherwise matched
    "/api/*": Response.json({ message: "Not found" }, { status: 404 }),
    
    // Redirect from /blog/hello to /blog/hello/world
    "/blog/hello": Response.redirect("/blog/hello/world"),

    // Serve a file by lazily loading it into memory
    "/fa": Bun.file("./static/index.html"),
  },

  // (optional) fallback for unmatched routes:
  // Required if Bun's version < 1.2.3
  fetch(req) {
    return new Response("Not Found", { status: 404 });
  },
});

console.log(`Server running at ${server.url}`);