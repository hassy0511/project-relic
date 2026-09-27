/// <reference types="vitest/config" />
import { defineConfig } from 'vite';

export default defineConfig({
  // 相対パスにして、GitHub Pages のサブパスでもローカルでも同じビルドで動かす
  base: './',
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 4000,
    rollupOptions: {
      // 見た目の確認ページ（lookdev.html）も一緒に公開する
      input: { main: 'index.html', lookdev: 'lookdev.html' },
    },
  },
  test: {
    include: ['tests/unit/**/*.test.ts', 'tests/sim/**/*.test.ts'],
    environment: 'node',
    testTimeout: 30000,
  },
});
