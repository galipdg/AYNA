import react from '@vitejs/plugin-react'
import { defineConfig } from 'electron-vite'
import type { Plugin } from 'vite'
import { contentSecurityPolicy } from './src/main/security.ts'

/** Injects the CSP meta tag so the policy has one source: src/main/security.ts. */
function cspMetaTag(): Plugin {
  let dev = false
  return {
    name: 'ayna-csp-meta',
    configResolved(config) {
      dev = config.command === 'serve'
    },
    transformIndexHtml() {
      return [
        {
          tag: 'meta',
          attrs: {
            'http-equiv': 'Content-Security-Policy',
            content: contentSecurityPolicy({ dev }),
          },
          injectTo: 'head-prepend',
        },
      ]
    },
  }
}

export default defineConfig({
  main: {},
  preload: {},
  renderer: {
    plugins: [cspMetaTag(), react()],
  },
})
