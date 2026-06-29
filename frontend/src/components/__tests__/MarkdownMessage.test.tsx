import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownMessage } from '../MarkdownMessage';

describe('MarkdownMessage', () => {
  it('renders GFM tables as real table elements', () => {
    render(
      <MarkdownMessage
        content={[
          '| 日期 | 降雨量 |',
          '| --- | ---: |',
          '| 6月21日 | 0 mm |',
          '| 6月22日 | 2.3 mm |',
        ].join('\n')}
      />,
    );

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '日期' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '2.3 mm' })).toBeInTheDocument();
  });
});
