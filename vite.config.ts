/// <reference types="vitest/config" />
import { defineConfig } from 'vite';

export default defineConfig({
  // 相対パスにして、GitHub Pages のサブパスでもローカルでも同じビルドで動かす
  base: './',
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 4000,
  },
  test: {
    include: ['tests/unit/**/*.test.ts', 'tests/sim/**/*.test.ts'],
    environment: 'node',
    testTimeout: 30000,
  },
});
