import { type EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { safeNext } from "@/lib/safe-next";

/**
 * Cel linków z maili (potwierdzenie rejestracji, reset hasła, magic link).
 * Obsługuje oba formaty, które może wysłać Supabase:
 *  - ?code=…                 (domyślne szablony maili, flow PKCE)
 *  - ?token_hash=…&type=…    (własne szablony maili)
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = safeNext(
    searchParams.get("next") ?? (type === "recovery" ? "/reset-password" : null),
  );

  const supabase = await createClient();
  let error: unknown = null;

  if (code) {
    ({ error } = await supabase.auth.exchangeCodeForSession(code));
  } else if (token_hash && type) {
    ({ error } = await supabase.auth.verifyOtp({ type, token_hash }));
  } else {
    return NextResponse.redirect(`${origin}/login?error=invalid_link`);
  }

  if (error) {
    return NextResponse.redirect(`${origin}/login?error=expired_link`);
  }
  return NextResponse.redirect(`${origin}${next}`);
}
