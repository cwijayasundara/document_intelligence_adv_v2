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
    // No manifest — use defaults
  }

  const typechecker = manifest && manifest.typechecker ? manifest.typechecker : null;
  const normalized = filePath.replace(/\\/g, '/');

  if (isPython) {
    const useChecker = typechecker ? typechecker === 'mypy' : true;
    if (useChecker) {
      const backendIdx = normalized.indexOf('/backend/');
      const cwd = backendIdx !== -1 ? normalized.substring(0, backendIdx + '/backend'.length) : process.cwd();
      const result = spawnSync('sh', ['-c', `uv run mypy "${filePath}"`], {
        encoding: 'utf8',
        shell: false,
        cwd,
        timeout: 25000,
      });
      if (result.status !== 0) {
        // Only report errors in the edited file, not the entire project
        const output = (result.stdout || '') + (result.stderr || '');
        const lines = output.split('\n');
        const basename = path.basename(filePath);
        const relevantErrors = lines.filter(line => line.includes(basename) && line.includes('error:'));
        if (relevantErrors.length > 0) {
          process.stderr.write(`Typecheck errors in ${filePath}:\n${relevantErrors.join('\n')}\nFix: Add type annotations or fix the type mismatch shown above.\n`);
        }
      }
    }
  } else if (isTypeScript) {
    const useChecker = typechecker ? typechecker === 'tsc' : true;
    if (useChecker) {
      const frontendIdx = normalized.indexOf('/frontend/');
      const cwd = frontendIdx !== -1 ? normalized.substring(0, frontendIdx + '/frontend'.length) : process.cwd();
      const result = spawnSync('sh', ['-c', 'npx tsc --noEmit --incremental --tsBuildInfoFile node_modules/.cache/.tsbuildinfo'], {
        encoding: 'utf8',
        shell: false,
        cwd,
        timeout: 25000,
      });
      if (result.status !== 0) {
        // Only report errors in the edited file
        const output = (result.stdout || '') + (result.stderr || '');
        const lines = output.split('\n');
        const basename = path.basename(filePath);
        const relevantErrors = lines.filter(line => line.includes(basename) && line.includes('error'));
        if (relevantErrors.length > 0) {
          process.stderr.write(`Typecheck errors (tsc):\n${relevantErrors.join('\n')}\nFix: Add type annotations or fix the type mismatch shown above.\n`);
        }
      }
    }
  }
} catch (err) {
  // Swallow hook errors so they don't block edits
}

process.exit(0);
