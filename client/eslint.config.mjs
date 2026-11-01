import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'
import tseslint from 'typescript-eslint'
import { defineConfig } from 'eslint/config'

export default defineConfig(
  { ignores: ['out/', 'release/', 'node_modules/'] },
  js.configs.recommended,
  tseslint.configs.recommended,
  {
    files: [
      'src/main/**/*.ts',
      'src/preload/**/*.ts',
      'src/shared/**/*.ts',
      '*.{ts,mjs}',
      'dev/**/*.mjs',
    ],
    languageOptions: { globals: globals.node },
  },
  {
    files: ['src/renderer/**/*.{ts,tsx}'],
    languageOptions: { globals: globals.browser },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // The renderer is sandboxed: Node built-ins and Electron are never available there.
      'no-restricted-imports': [
        'error',
        { patterns: ['node:*', 'electron', '**/main/**', '**/preload/**'] },
      ],
    },
  },
  prettier,
)
