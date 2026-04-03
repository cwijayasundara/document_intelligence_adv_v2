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
  const normalized = filePath.replace(/\\/g, '/');

  if (isPython) {
    const useLinter = linter ? linter === 'ruff' : true;
    if (useLinter) {
      const backendIdx = normalized.indexOf('/backend/');
      const cwd = backendIdx !== -1 ? normalized.substring(0, backendIdx + '/backend'.length) : process.cwd();
      // Run auto-fix silently; only report unfixable errors
      const result = spawnSync('sh', ['-c', `uv run ruff check --fix "${filePath}" 2>&1 && uv run ruff format "${filePath}" 2>&1`], {
        encoding: 'utf8',
        shell: false,
        cwd,
        timeout: 10000,
      });
      if (result.status !== 0) {
        const output = (result.stdout || '').trim();
        if (output) {
          process.stderr.write(`Lint errors in ${filePath}:\n${output}\n`);
        }
      }
    }
  } else if (isTypeScript) {
    const useLinter = linter ? linter === 'eslint' : true;
    if (useLinter) {
      const frontendIdx = normalized.indexOf('/frontend/');
      const cwd = frontendIdx !== -1 ? normalized.substring(0, frontendIdx + '/frontend'.length) : process.cwd();
      const result = spawnSync('sh', ['-c', `npx eslint --fix "${filePath}" 2>&1`], {
        encoding: 'utf8',
        shell: false,
        cwd,
        timeout: 10000,
      });
      if (result.status !== 0) {
        const output = (result.stdout || '').trim();
        if (output) {
          process.stderr.write(`Lint errors in ${filePath}:\n${output}\n`);
        }
      }
    }
  }
} catch (_) {
  // Swallow hook errors so they don't block edits
}

process.exit(0);
