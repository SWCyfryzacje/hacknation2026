import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/** Klient Supabase dla Server Components, Server Actions i Route Handlers. */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Server Component nie może zapisywać ciasteczek. Odświeżanie tokenu
            // obsługuje proxy.ts, więc ten przypadek można zignorować.
          }
        },
      },
    },
  );
}
