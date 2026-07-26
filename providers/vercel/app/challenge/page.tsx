// idk if this actually works its vibecoded slop that says yes - todo unslopify
"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

type VerifyResult = { success: boolean; isBot?: boolean; error?: string };

function Challenge() {
  const params = useSearchParams();
  const name = params.get("name") ?? "anonymous";
  const [state, setState] = useState<"idle" | "checking" | "done">("idle");
  const [result, setResult] = useState<VerifyResult | null>(null);
  
  // Guard ref prevents duplicate execution in React Strict Mode
  const hasTriggered = useRef(false);

  async function solve() {
    setState("checking");
    try {
      const res = await fetch(
        `/api/botid?name=${encodeURIComponent(name)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );
      setResult((await res.json()) as VerifyResult);
    } catch (e) {
      setResult({ success: false, error: String(e) });
    } finally {
      setState("done");
    }
  }

  // Automatically trigger the check on component mount
  useEffect(() => {
    if (!hasTriggered.current) {
      hasTriggered.current = true;
      solve();
    }
  }, [name]); // Re-runs if the URL name parameter changes

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Vercel BotID Challenge</h1>
      <p>
        Invisibly proving you are (not) a bot for the glory of <b>{name}</b>.
      </p>
      
      {/* UI state message replacing the manual button */}
      <div>
        {state === "checking" && <p>🤖 Checking your browser...</p>}
        {state === "done" && <p>✅ Check complete.</p>}
      </div>

      {result && (
        <p id="results">
          Success: {String(result.success)}
          {result.error ? ` (${result.error})` : ""}
        </p>
      )}
    </main>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<main style={{ padding: "2rem" }}>Loading...</main>}>
      <Challenge />
    </Suspense>
  );
}

// "use client";

// import { Suspense, useEffect, useRef, useState } from "react";
// import { useSearchParams } from "next/navigation";

// // The challenge page. Served from Vercel so that:
// //   1. initBotId() has run (see instrumentation-client.ts), and
// //   2. the fetch below is SAME-ORIGIN, so BotID actually attaches its headers.
// // A user clicks "Solve Vercel BotID" on the Nest homepage, lands here with
// // ?name=Foo, and this page fires the invisible check.

// type VerifyResult = { success: boolean; isBot?: boolean; error?: string };

// function Challenge() {
//   const params = useSearchParams();
//   const name = params.get("name") ?? "anonymous";
//   const [state, setState] = useState<"idle" | "checking" | "done">("idle");
//   const [result, setResult] = useState<VerifyResult | null>(null);

//   async function solve() {
//     setState("checking");
//     try {
//       const res = await fetch(
//         `/api/botid?name=${encodeURIComponent(name)}`,
//         { method: "POST", headers: { "Content-Type": "application/json" } },
//       );
//       setResult((await res.json()) as VerifyResult);
//     } catch (e) {
//       setResult({ success: false, error: String(e) });
//     } finally {
//       setState("done");
//     }
//   }

//   return (
//     <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
//       <h1>Vercel BotID Challenge</h1>
//       <p>
//         Invisibly proving you are (not) a bot for the glory of <b>{name}</b>.
//       </p>
//       <button onClick={solve} disabled={state === "checking"}>
//         {state === "checking" ? "Checking..." : "Attempt the challenge"}
//       </button>
//       {result && (
//         <p id="results">
//           Success: {String(result.success)}
//           {result.error ? ` (${result.error})` : ""}
//         </p>
//       )}
//     </main>
//   );
// }

// export default function Page() {
//   return (
//     <Suspense fallback={<main style={{ padding: "2rem" }}>Loading...</main>}>
//       <Challenge />
//     </Suspense>
//   );
// }
