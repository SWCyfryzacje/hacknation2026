export type ResultTab = 'preview' | 'report' | 'json';

export interface ResultTabItem {
  id: ResultTab;
  label: string;
}

export function getResultTabs(
  hasReport: boolean,
  enableJsonDebug: boolean,
): ResultTabItem[] {
  return [
    { id: 'preview', label: 'Podgląd formularza' },
    ...(hasReport ? [{ id: 'report' as const, label: 'Raport' }] : []),
    ...(enableJsonDebug ? [{ id: 'json' as const, label: 'JSON' }] : []),
  ];
}