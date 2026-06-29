import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Modal } from '../Modal';

describe('Modal Component', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <Modal isOpen={false} title="Test Title" onClose={() => {}}>
        <div>Modal Content</div>
      </Modal>
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders title and content when isOpen is true', () => {
    render(
      <Modal isOpen={true} title="Test Title" onClose={() => {}}>
        <div>Modal Content</div>
      </Modal>
    );
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Modal Content')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} title="Test Title" onClose={handleClose}>
        <div>Modal Content</div>
      </Modal>
    );

    // Click cancel or X button. Let's find by label or text.
    // We will provide a button with aria-label="关闭弹窗" or text "取消"
    const closeBtn = screen.getByLabelText('关闭弹窗');
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onConfirm when confirm button is clicked', () => {
    const handleConfirm = vi.fn();
    render(
      <Modal isOpen={true} title="Test Title" onClose={() => {}} onConfirm={handleConfirm} confirmText="确认">
        <div>Modal Content</div>
      </Modal>
    );

    const confirmBtn = screen.getByText('确认');
    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });
});
