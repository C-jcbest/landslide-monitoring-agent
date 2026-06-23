import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThinkingIndicator } from '../ThinkingIndicator';

describe('ThinkingIndicator Component', () => {
  it('renders with default status text', () => {
    render(<ThinkingIndicator />);
    expect(screen.getByText('Agent 正在分析监测数据并加载回复...')).toBeInTheDocument();
  });

  it('renders with custom status text', () => {
    render(<ThinkingIndicator statusText="监测计算中..." />);
    expect(screen.getByText('监测计算中...')).toBeInTheDocument();
  });
});
