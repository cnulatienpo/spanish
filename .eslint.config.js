// Minimal flat ESLint config for mixed React/Node JS projects
import js from '@eslint/js'

export default [
  { ignores: ['**/node_modules/**', '**/dist/**', '**/build/**'] },
  {
    files: ['**/*.js', '**/*.jsx'],
    languageOptions: { ecmaVersion: 2023, sourceType: 'module' },
    rules: {
      ...js.configs.recommended.rules,
    },
  },
]
