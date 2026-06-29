import { afterEach, describe, expect, it, vi } from 'vitest';
import { streamChat } from '../api';

function makeStream(chunks: string[]) {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

function mockStreamResponse(chunks: string[], ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      body: makeStream(chunks),
      text: async () => 'request failed',
    }),
  );
}

describe('streamChat', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('streams content chunks and calls onDone after done event', async () => {
    mockStreamResponse([
      'data: {"content":"滑坡","done":false}\n\n',
      'data: {"content":"风险","done":false}\n\n',
      'data: {"content":"","done":true}\n\n',
    ]);

    const onChunk = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    await streamChat([{ role: 'user', content: '查询风险' }], 'token', onChunk, onDone, onError);

    expect(onChunk).toHaveBeenNthCalledWith(1, '滑坡');
    expect(onChunk).toHaveBeenNthCalledWith(2, '风险');
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it('reports server error events through onError', async () => {
    mockStreamResponse(['data: {"event":"error","error":"模型调用失败","done":true}\n\n']);

    const onError = vi.fn();

    await streamChat([{ role: 'user', content: '查询风险' }], 'token', vi.fn(), vi.fn(), onError);

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][0].message).toBe('模型调用失败');
  });

  it('reports premature stream end when no done event is received', async () => {
    mockStreamResponse(['data: {"content":"未结束","done":false}\n\n']);

    const onError = vi.fn();

    await streamChat([{ role: 'user', content: '查询风险' }], 'token', vi.fn(), vi.fn(), onError);

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0].message).toBe('Stream ended before completion');
  });

  it('passes abort signal to fetch', async () => {
    mockStreamResponse(['data: {"content":"","done":true}\n\n']);
    const controller = new AbortController();

    await streamChat([{ role: 'user', content: '查询风险' }], 'token', vi.fn(), vi.fn(), vi.fn(), {
      signal: controller.signal,
    });

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/chatbot/chat/stream',
      expect.objectContaining({ signal: controller.signal }),
    );
  });
});
