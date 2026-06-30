import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { HumanPromptCard } from '../HumanPromptCard';

describe('HumanPromptCard Component', () => {
  it('renders correctly with given question', () => {
    render(<HumanPromptCard question="是否确认滑坡隐患点 A 的阈值？" onSubmit={() => {}} loading={false} />);
    
    expect(screen.getByText('监测人工干预请求')).toBeInTheDocument();
    expect(screen.getByText('是否确认滑坡隐患点 A 的阈值？')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('输入您的确认说明或答复以继续监测...')).toBeInTheDocument();
  });

  it('submits response correctly when form is submitted', () => {
    const handleSubmit = vi.fn();
    render(<HumanPromptCard question="测试干预" onSubmit={handleSubmit} loading={false} />);
    
    const textarea = screen.getByPlaceholderText('输入您的确认说明或答复以继续监测...');
    const submitBtn = screen.getByRole('button', { name: '提交人工干预回复' });
    
    // Initial state: button should be disabled since text is empty
    expect(submitBtn).toBeDisabled();
    
    // Change value
    fireEvent.change(textarea, { target: { value: '已检查，无风险。' } });
    expect(submitBtn).not.toBeDisabled();
    
    // Submit form
    fireEvent.click(submitBtn);
    expect(handleSubmit).toHaveBeenCalledWith('已检查，无风险。');
    
    // Textarea should be cleared after submit
    expect(textarea).toHaveValue('');
  });

  it('updates textarea value when clicking quick response pills', () => {
    render(<HumanPromptCard question="测试干预" onSubmit={() => {}} loading={false} />);
    
    const textarea = screen.getByPlaceholderText('输入您的确认说明或答复以继续监测...');
    
    // Click the first quick response pill
    const pill = screen.getByRole('button', { name: '确认无误，请继续执行。' });
    fireEvent.click(pill);
    
    expect(textarea).toHaveValue('确认无误，请继续执行。');
  });

  it('disables input, button, and pills when loading is true', () => {
    render(<HumanPromptCard question="测试干预" onSubmit={() => {}} loading={true} />);
    
    const textarea = screen.getByPlaceholderText('输入您的确认说明或答复以继续监测...');
    const submitBtn = screen.getByRole('button', { name: '提交人工干预回复' });
    const pill = screen.getByRole('button', { name: '确认无误，请继续执行。' });
    
    expect(textarea).toBeDisabled();
    expect(submitBtn).toBeDisabled();
    expect(pill).toBeDisabled();
    expect(screen.getByText('正在恢复 Agent...')).toBeInTheDocument();
  });
});
