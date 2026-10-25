import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'

export default [
  { ignores: ['out/', 'release/', 'node_modules/'] },
  js.configs.recommended,
  {
    files: ['src/main/**/*.js', 'src/preload/**/*.js', 'src/shared/**/*.js', '*.mjs'],
    languageOptions: { globals: globals.node },
  },
  {
    files: ['src/renderer/**/*.{js,jsx}'],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
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
]
