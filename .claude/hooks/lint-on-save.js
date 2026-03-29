#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

try {
  const input = JSON.parse(fs.readFileSync('/dev/stdin', 'utf8'));
  const filePath = (input.tool_input && input.tool_input.file_path) || '';

  if (!filePath) {
    process.exit(0);
  }

  const ext = path.extname(filePath).toLowerCase();
  const isPython = ext === '.py';
  const isTypeScript = ext === '.ts' || ext === '.tsx';

  if (!isPython && !isTypeScript) {
    process.exit(0);
  }

  // Try to read project-manifest.json
  let manifest = null;
  try {
    const manifestPath = path.join(process.cwd(), 'project-manifest.json');
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  } catch (_) {
    // No manifest — use fallback defaults
  }

  const linter = manifest && manifest.linter ? manifest.linter : null;

  if (isPython) {
    const useLinter = linter ? linter === 'ruff' : true; // fallback: use ruff
    if (useLinter) {
      spawnSync('sh', ['-c', `uv run ruff check --fix "${filePath}" && uv run ruff format "${filePath}"`], {
        stdio: 'inherit',
        shell: false,
      });
    }
  } else if (isTypeScript) {
    const useLinter = linter ? linter === 'eslint' : true; // fallback: use eslint
    if (useLinter) {
      spawnSync('sh', ['-c', `npx eslint --fix "${filePath}"`], {
        stdio: 'inherit',
        shell: false,
      });
    }
  }
} catch (lintErr) {
  process.stderr.write(`lint-on-save: auto-fix failed — ${lintErr.message}\nFix: Review the linter output above and resolve any unfixable issues manually before saving.\n`);
}

process.exit(0);
