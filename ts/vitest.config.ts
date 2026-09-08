import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    // The corpus parity suite parses ~90 files, each in its own session, and
    // each session loads the standard library. The default 5 s is not enough
    // and a timeout here reads as a hang rather than as a budget.
    testTimeout: 120_000,
  },
});
