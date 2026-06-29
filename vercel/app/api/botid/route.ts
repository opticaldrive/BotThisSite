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

  if (verification.isBot) {
    // Detected as a bot -> no solve recorded.
    return NextResponse.json({ success: false, isBot: true });
  }

  // Human (slipped past the invisible detector) -> record the solve on Nest.
  if (!FASTAPI_BASE_URL || !BOTID_SHARED_SECRET) {
    return NextResponse.json(
      { success: false, error: "shim not configured (missing env)" },
      { status: 500 },
    );
  }

  try {
    const res = await fetch(`${FASTAPI_BASE_URL}/captchas/record`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-BotID-Secret": BOTID_SHARED_SECRET,
      },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) {
      return NextResponse.json(
        { success: false, error: `record failed: ${res.status}` },
        { status: 502 },
      );
    }
    return NextResponse.json({ success: true, isBot: false });
  } catch (e) {
    return NextResponse.json(
      { success: false, error: String(e) },
      { status: 502 },
    );
  }
}
