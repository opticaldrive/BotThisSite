import { checkBotId } from "botid/server";
import { NextResponse, type NextRequest } from "next/server";

// Server-side BotID check. The client (challenge page) must have listed this
// exact route in initBotId().protect, otherwise checkBotId() sees no headers
// and reports a bot.
//
// "Solving" BotThisSite's BotID == being classified as NOT a bot. On success we
// report the solve to the FastAPI app on Nest, authenticated with a shared
// secret so randoms can't POST fake solves to /captchas/record directly.

const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL; // e.g. https://bts.zzz.hackclub.app
const BOTID_SHARED_SECRET = process.env.BOTID_SHARED_SECRET;

export async function POST(request: NextRequest) {
  const name = request.nextUrl.searchParams.get("name") ?? "anonymous";

  const verification = await checkBotId();
  const success = !verification.isBot;

  // "success" is purely the BotID verdict. Recording the solve on Nest is an
  // optional second step: when the FastAPI env vars aren't set, we skip it, so
  // you can deploy this shim and test the Success: True/False UI standalone
  // without any FastAPI changes.
  if (!success || !FASTAPI_BASE_URL || !BOTID_SHARED_SECRET) {
    return NextResponse.json({
      success,
      isBot: verification.isBot,
      recorded: false,
    });
  }

  // Human (slipped past the invisible detector) -> record the solve on Nest.
  try {
    const res = await fetch(`${FASTAPI_BASE_URL}/captchas/record`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-BotID-Secret": BOTID_SHARED_SECRET,
      },
      body: JSON.stringify({ name }),
    });
    return NextResponse.json({
      success,
      isBot: verification.isBot,
      recorded: res.ok,
      ...(res.ok ? {} : { error: `record failed: ${res.status}` }),
    });
  } catch (e) {
    return NextResponse.json({
      success,
      isBot: verification.isBot,
      recorded: false,
      error: String(e),
    });
  }
}
