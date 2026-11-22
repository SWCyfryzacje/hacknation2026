export const allowedDocumentExtensions = [
  '.pdf',
  '.doc',
  '.docx',
  '.ods',
  '.xlsx',
  '.jpg',
  '.jpeg',
  '.png',
];

const forbiddenCharacters = /[;:></\\|'*%$]/;

export function validateDocumentFile(
  file: Pick<File, 'name' | 'size'>,
): string | null {
  const extension = file.name.includes('.')
    ? file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    : '';

  if (!allowedDocumentExtensions.includes(extension)) {
    return `Nieobsługiwany format „${extension || 'brak rozszerzenia'}”. Dozwolone: ${allowedDocumentExtensions.join(', ')}.`;
  }
  if (file.name.length > 250) {
    return 'Nazwa pliku nie może przekraczać 250 znaków.';
  }
  if (forbiddenCharacters.test(file.name)) {
    return "Nazwa pliku zawiera niedozwolone znaki: ; : > < / \\ | ' * % $.";
  }
  if (file.size === 0) {
    return 'Plik jest pusty.';
  }

  return null;
}