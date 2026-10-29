import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const webRoot = fileURLToPath(new URL('./web', import.meta.url))

export default defineConfig({
  root: webRoot,
  // 相对路径打包：dist/index.html 可以直接双击打开，不依赖任何后台服务
  base: './',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
  },
})
