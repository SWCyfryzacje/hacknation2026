import { describe, expect, it } from 'vitest';
import sampleFormJson from '../../../test.json?raw';
import {
  isFormConfiguration,
  type FormConfiguration,
  type FormField,
} from '@/types/form';
import {
  createInitialAnswers,
  getAllFields,
  isUserVisibleField,
  orderPageQuestions,
  orderTabs,
} from './utils';
import { validateField } from './validators';
import { evaluateVisibility } from './visibility';

function makeField(overrides: Partial<FormField> = {}): FormField {
  return {
    id: 'field-id',
    type: 'TEXT_FIELD',
    techName: 'field_name',
    ...overrides,
  };
}

describe('orderTabs', () => {
  it('follows flow links instead of relying on the tabs array order', () => {
    const form: FormConfiguration = {
      tabs: [
        { id: 'third', title: 'Third' },
        { id: 'first', title: 'First' },
        { id: 'second', title: 'Second' },
      ],
      flow: {
        links: [
          { source: 'first', target: 'second' },
          { source: 'second', target: 'third' },
        ],
      },
    };

    expect(orderTabs(form).map((tab) => tab.id)).toEqual([
      'first',
      'second',
      'third',
    ]);
  });

  it('falls back to the tabs array when the flow is incomplete', () => {
    const form: FormConfiguration = {
      tabs: [
        { id: 'first', title: 'First' },
        { id: 'second', title: 'Second' },
      ],
      flow: { links: [{ source: 'first', target: 'missing' }] },
    };

    expect(orderTabs(form)).toBe(form.tabs);
  });
});

describe('createInitialAnswers', () => {
  it('maps external defaults and preserves checkbox selections', () => {
    const form: FormConfiguration = {
      tabs: [
        {
          id: 'page',
          questions: [
            {
              field: makeField({
                id: 'section',
                type: 'SECTION',
                techName: 'section',
                repeatingSectionGrid: [
                  {
                    field: makeField({
                      id: 'name',
                      techName: 'name',
                      defaultValue: 'MLPZ.name',
                      defaultValueType: 'EXTERNAL_SYSTEM',
                    }),
                  },
                  {
                    field: makeField({
                      id: 'choices',
                      type: 'CHECKBOX',
                      techName: 'choices',
                      defaultValue: ['One', 'Two'],
                    }),
                  },
                ],
              }),
            },
          ],
        },
      ],
    };

    expect(createInitialAnswers(form)).toEqual({
      name: 'Jan',
      choices: ['One', 'Two'],
    });
  });
});

describe('isUserVisibleField', () => {
  it('hides fields with TERYT in any name without altering form data', () => {
    const fields = [
      makeField({ techName: 'TERYT_address' }),
      makeField({ title: 'Dane TERYT adresu' }),
      makeField({ dictionaryName: 'TERYT_4G_DOWODOWY' }),
    ];

    expect(fields.every((field) => !isUserVisibleField(field))).toBe(true);
    expect(fields[0].techName).toBe('TERYT_address');
    expect(fields[1].title).toBe('Dane TERYT adresu');
    expect(fields[2].dictionaryName).toBe('TERYT_4G_DOWODOWY');
    expect(
      validateField({ ...fields[0], validation: ['REQUIRED'] }, undefined),
    ).toBeNull();
    expect(isUserVisibleField(makeField({ title: 'Inne pole' }))).toBe(true);
  });
});

describe('validateField', () => {
  it('rejects missing required values and accepts valid PESEL, NIP, and REGON values', () => {
    expect(validateField(makeField({ validation: ['REQUIRED'] }), '')).toBe(
      'To pole jest wymagane.',
    );
    expect(
      validateField(makeField({ validation: ['PESEL'] }), '44051401359'),
    ).toBeNull();
    expect(
      validateField(makeField({ validation: ['NIP'] }), '5260250995'),
    ).toBeNull();
    expect(
      validateField(makeField({ validation: ['REGON'] }), '590096454'),
    ).toBeNull();
  });

  it('reports invalid postal, email, identity-card, and e-delivery values', () => {
    expect(validateField(makeField({ validation: ['ZIP_CODE'] }), '1234')).toBe(
      'Wpisz kod pocztowy w formacie 00-000.',
    );
    expect(validateField(makeField({ validation: ['EMAIL'] }), 'not-an-email')).toBe(
      'Wpisz poprawny adres e-mail.',
    );
    expect(
      validateField(
        makeField({ validation: ['SERIAL_NUMBER_ID_CARD'] }),
        'ABC123',
      ),
    ).toBe('Wpisz serię i numer dowodu, np. ABC123456.');
    expect(validateField(makeField({ validation: ['ADE'] }), 'invalid')).toBe(
      'Wpisz adres do e-Doręczeń, np. AE:PL-12345-67890-ABCDE-12.',
    );
  });

  it('requires each consent marked as required', () => {
    const field = makeField({
      type: 'CONSENT_SECTION',
      consentSectionConfig: {
        consents: [{ required: true }, { required: false }],
      },
    });

    expect(validateField(field, [false, true])).toBe('Zaznacz wymagane zgody.');
    expect(validateField(field, [true, false])).toBeNull();
  });
});

describe('evaluateVisibility', () => {
  const form: FormConfiguration = {
    tabs: [
      {
        id: 'page',
        title: 'Dane',
        questions: [
          {
            field: makeField({
              id: 'address',
              type: 'SECTION',
              techName: 'address',
              repeatingSectionGrid: [
                {
                  field: makeField({ id: 'country', techName: 'country' }),
                },
                {
                  field: makeField({
                    id: 'abroad-city',
                    techName: 'abroad_city',
                    states: [
                      {
                        type: 'SHOW',
                        query:
                          '("Polska" in tabs[0].questions[0].field.repeatingSectionGrid[0].field.__userAnswer)',
                      },
                    ],
                  }),
                },
              ],
            }),
          },
        ],
      },
    ],
  };

  it('updates conditional visibility as answers change', async () => {
    await expect(evaluateVisibility(form, { country: 'Polska' })).resolves.toMatchObject({
      'abroad-city': true,
    });
    await expect(evaluateVisibility(form, { country: 'Niemcy' })).resolves.toMatchObject({
      'abroad-city': false,
    });
  });

  it('shows the other-person name and PESEL fields when that applicant is selected', async () => {
    const sampleForm = JSON.parse(sampleFormJson) as FormConfiguration;
    const dataPage = sampleForm.tabs.find((tab) => tab.title === 'Dane');
    const fields = getAllFields(sampleForm);
    const otherPersonSection = fields.find(
      (field) => field.techName === 'dane_innej_osoby',
    );
    const otherPersonFields = fields.filter((field) =>
      ['imie_inna_osoba', 'nazwisko_inna_osoba', 'numer_pesel_inna_osoba'].includes(
        field.techName,
      ),
    );

    expect(otherPersonSection).toBeDefined();
    expect(otherPersonFields).toHaveLength(3);
    expect(dataPage).toBeDefined();

    const orderedQuestions = orderPageQuestions(dataPage!.questions ?? []);
    const applicantIndex = orderedQuestions.findIndex(
      (question) => question.field.techName === 'podmiot_wniosku',
    );
    expect(orderedQuestions[applicantIndex + 1].field.techName).toBe(
      'dane_innej_osoby',
    );

    const visibleForOtherPerson = await evaluateVisibility(sampleForm, {
      wybierz_w_czyim_imieniu_wnioskujesz: 'Innej osoby',
    });
    const visibleForSelf = await evaluateVisibility(sampleForm, {
      wybierz_w_czyim_imieniu_wnioskujesz: 'Swoim',
    });

    expect(visibleForOtherPerson[otherPersonSection!.id]).toBe(true);
    expect(otherPersonFields.every((field) => visibleForOtherPerson[field.id])).toBe(
      true,
    );
    expect(visibleForSelf[otherPersonSection!.id]).toBe(false);
  });
});

describe('sample form configuration', () => {
  const parsed: unknown = JSON.parse(sampleFormJson);

  it('validates and orders all linked sample pages', () => {
    expect(isFormConfiguration(parsed)).toBe(true);
    if (!isFormConfiguration(parsed)) return;

    expect(orderTabs(parsed).map((tab) => tab.title)).toEqual([
      'Dane',
      'Informacje o budynku',
      'Kontakt i zgody',
      'Strona końcowa',
    ]);
  });

  it('updates sample address conditions when the country answer changes', async () => {
    if (!isFormConfiguration(parsed)) throw new Error('Sample form is invalid.');

    const fieldsByName = new Map(
      getAllFields(parsed).map((field) => [field.techName, field]),
    );
    const defaults = createInitialAnswers(parsed);
    expect(defaults.kraj).toBe('Polska');

    const polishAddress = await evaluateVisibility(parsed, defaults);
    expect(polishAddress[fieldsByName.get('miejscowosc_zagranica')!.id]).toBe(
      false,
    );
    expect(polishAddress[fieldsByName.get('wojewodztwo')!.id]).toBe(true);

    const foreignAddress = await evaluateVisibility(parsed, {
      ...defaults,
      kraj: 'Niemcy',
    });
    expect(foreignAddress[fieldsByName.get('miejscowosc_zagranica')!.id]).toBe(
      true,
    );
    expect(foreignAddress[fieldsByName.get('wojewodztwo')!.id]).toBe(false);
  });
});