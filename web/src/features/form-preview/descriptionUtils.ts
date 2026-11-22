export function hasDescriptionText(markup?: string): boolean {
  if (!markup) return false;
  return Boolean(
    new DOMParser()
      .parseFromString(markup, 'text/html')
      .body.textContent?.trim().length,
  );
}