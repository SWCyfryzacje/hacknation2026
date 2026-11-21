/**
 * Zwraca bezpieczną ścieżkę przekierowania (tylko w obrębie naszej domeny).
 * Odrzuca "//evil.com" i "/\evil.com", które przeglądarka traktuje jak inny host.
 */
export function safeNext(value: unknown, fallback = "/panel"): string {
  if (typeof value !== "string") return fallback;
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return fallback;
  }
  return value;
}
