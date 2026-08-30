import { defineConfig } from 'vitest/config';
import path from 'node:path';

// Chỉ chạy test của phần NGHIÊN CỨU (engine ký hiệu + bench). Không có phần app.
export default defineConfig({
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  test: {
    include: [
      'api/_lib/kernel/**/*.test.ts',
      'api/_lib/__tests__/**/*.test.js',
      'api/_lib/bench/__tests__/**/*.test.js',
    ],
    environment: 'node',
    fileParallelism: false,
    maxWorkers: 1,
    minWorkers: 1,
  },
});
