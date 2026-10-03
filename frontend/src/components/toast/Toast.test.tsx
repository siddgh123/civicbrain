import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ToastProvider } from './ToastProvider';
import { useToast } from './useToast';

function Trigger() {
  const { show } = useToast();
  return (
    <button type="button" onClick={() => show({ message: 'Plan approved', tone: 'success' })}>
      go
    </button>
  );
}

describe('Toast', () => {
  it('announces the message in an aria-live region and can be dismissed', async () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'go' }));

    const toast = screen.getByTestId('toast');
    expect(toast).toHaveTextContent('Plan approved');
    expect(toast.closest('[aria-live="polite"]')).not.toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));
    expect(screen.queryByTestId('toast')).not.toBeInTheDocument();
  });
});
