import jsonata from 'jsonata';
import type { FormConfiguration } from '@/types/form';
import { getAllFields } from './utils';

const expressionCache = new Map<string, ReturnType<typeof jsonata>>();

export async function evaluateVisibility(
  form: FormConfiguration,
  answers: Record<string, unknown>,
): Promise<Record<string, boolean>> {
  const formWithAnswers = structuredClone(form);
  const fields = getAllFields(formWithAnswers);

  for (const field of fields) {
    field.__userAnswer = answers[field.techName];
  }

  const visibility: Record<string, boolean> = {};
  for (const field of fields) {
    let isVisible = true;
    for (const condition of field.states ?? []) {
      if (condition.type !== 'SHOW' || !condition.query) continue;

      try {
        let expression = expressionCache.get(condition.query);
        if (!expression) {
          expression = jsonata(condition.query);
          expressionCache.set(condition.query, expression);
        }
        if (!(await expression.evaluate(formWithAnswers))) {
          isVisible = false;
          break;
        }
      } catch (error: unknown) {
        console.warn(`Nie udało się obliczyć warunku pola ${field.techName}:`, error);
      }
    }
    visibility[field.id] = isVisible;
  }

  return visibility;
}