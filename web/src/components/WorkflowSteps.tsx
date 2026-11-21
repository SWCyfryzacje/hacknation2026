type WorkflowStep = 'upload' | 'form';

interface WorkflowStepsProps {
  activeStep: WorkflowStep;
}

const steps: { id: WorkflowStep; label: string }[] = [
  { id: 'upload', label: 'Prześlij dokument' },
  { id: 'form', label: 'Sprawdź formularz' },
];

export function WorkflowSteps({ activeStep }: WorkflowStepsProps) {
  return (
    <nav aria-label='Etapy przetwarzania' className='mb-8'>
      <ol className='grid grid-cols-2 gap-3'>
        {steps.map((step, index) => {
          const isActive = step.id === activeStep;
          const isComplete = index === 0 && activeStep === 'form';

          return (
            <li
              aria-current={isActive ? 'step' : undefined}
              className={`flex items-center gap-3 border-b-2 pb-3 ${
                isActive || isComplete
                  ? 'border-blue-700 text-blue-800'
                  : 'border-slate-200 text-slate-500'
              }`}
              key={step.id}
            >
              <span
                aria-hidden='true'
                className={`flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  isActive || isComplete
                    ? 'bg-blue-700 text-white'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {isComplete ? '✓' : index + 1}
              </span>
              <span className='text-sm font-semibold sm:text-base'>
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}