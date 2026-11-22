import type {
  FormConfiguration,
  FormField,
  FormTab,
} from '@/types/form';
import type { ProposedDictionary } from '@/types/report';

const sampleData: Record<string, string> = {
  name: 'Jan',
  secondName: 'Piotr',
  surname: 'Kowalski',
  pesel: '44051401359',
  phoneNumber: '600 100 200',
  email: 'jan.kowalski@example.pl',
  country: 'Polska',
  voivodeship: 'kujawsko-pomorskie',
  district: 'Toruń',
  community: 'Toruń',
  place: 'Toruń',
  postCode: '87-100',
  street: 'Polna',
  building: '1',
  apartment: '2',
  birthDate: '1944-05-14',
  citizenship: 'polskie',
  sex: 'mężczyzna',
  familyName: 'Kowalski',
};

const countries = [
  'Polska',
  'Niemcy',
  'Czechy',
  'Słowacja',
  'Ukraina',
  'Litwa',
  'Białoruś',
  'Rosja',
  'Łotwa',
  'Francja',
  'Wielka Brytania',
  'Irlandia',
  'Holandia',
  'Belgia',
  'Norwegia',
  'Szwecja',
  'Dania',
  'Włochy',
  'Hiszpania',
  'Austria',
  'Stany Zjednoczone',
  'Kanada',
  'Inny kraj',
];

export function sortByPosition<T extends { x?: number; y?: number }>(
  items: T[],
): T[] {
  return [...items].sort(
    (left, right) => (left.y ?? 0) - (right.y ?? 0) || (left.x ?? 0) - (right.x ?? 0),
  );
}

export function orderTabs(form: FormConfiguration): FormTab[] {
  const tabs = form.tabs;
  const links = form.flow?.links ?? [];
  const tabsById = new Map(
    tabs.filter((tab) => tab.id).map((tab) => [tab.id as string, tab]),
  );
  const targetIds = new Set(links.map((link) => link.target));
  let current = tabs.find(
    (tab) =>
      tab.id &&
      !targetIds.has(tab.id) &&
      links.some((link) => link.source === tab.id),
  );
  const ordered: FormTab[] = [];
  const seen = new Set<string>();

  while (current?.id && !seen.has(current.id)) {
    ordered.push(current);
    seen.add(current.id);
    const link = links.find((candidate) => candidate.source === current?.id);
    current = link ? tabsById.get(link.target) : undefined;
  }

  return ordered.length === tabs.length ? ordered : tabs;
}

export function getAllFields(form: FormConfiguration): FormField[] {
  const fields: FormField[] = [];

  function addField(field: FormField) {
    fields.push(field);
    for (const child of field.repeatingSectionGrid ?? []) {
      addField(child.field);
    }
  }

  for (const tab of form.tabs) {
    for (const question of tab.questions ?? []) {
      addField(question.field);
    }
  }

  return fields;
}

export function isUserVisibleField(field: FormField): boolean {
  return ![field.techName, field.title, field.dictionaryName].some((name) =>
    name?.toUpperCase().includes('TERYT'),
  );
}

function getInitialAnswer(field: FormField): unknown {
  const defaultValue = field.defaultValue;
  if (defaultValue === undefined || defaultValue === null || defaultValue === '') {
    return undefined;
  }

  if (field.defaultValueType === 'EXTERNAL_SYSTEM') {
    const attribute = String(defaultValue).split('.').pop() ?? '';
    return sampleData[attribute] ?? `(${defaultValue})`;
  }

  if (Array.isArray(defaultValue)) {
    return field.type === 'CHECKBOX' ? defaultValue : defaultValue[0];
  }

  return defaultValue;
}

export function createInitialAnswers(
  form: FormConfiguration,
): Record<string, unknown> {
  const answers: Record<string, unknown> = {};
  for (const field of getAllFields(form)) {
    const initialAnswer = getInitialAnswer(field);
    if (initialAnswer !== undefined) answers[field.techName] = initialAnswer;
  }
  return answers;
}

export function getFieldOptions(
  field: FormField,
  dictionaries: ProposedDictionary[],
): string[] | null {
  if (field.options?.length) {
    return field.options.map((option) => option.name || option.id || '');
  }
  if (!field.dictionaryName) return null;
  if (field.dictionaryName === 'Kraje') return countries;
  return (
    dictionaries.find((dictionary) => dictionary.name === field.dictionaryName)
      ?.values ?? null
  );
}

export function getDictionaryHint(field: FormField): string {
  return /TERYT|Wojew|Powiat|Gmina|Miejscow/i.test(field.dictionaryName ?? '')
    ? 'Słownik TERYT — w podglądzie pole tekstowe'
    : `Słownik „${field.dictionaryName}” — w podglądzie pole tekstowe`;
}
