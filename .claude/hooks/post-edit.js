#!/usr/bin/env node

/**
 * Unified post-edit hook. Replaces 8 separate hooks to avoid
 * stdin piping issues in the Claude Code hook runner.
 *
 * Runs: scope-directory, protect-env, detect-secrets,
 *       lint-on-save, check-architecture, check-function-length,
 *       check-file-length.
 *
 * Typecheck is intentionally excluded (too slow for per-edit).
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

let input;
try {
  input = JSON.parse(fs.readFileSync('/dev/stdin', 'utf8'));
} catch (_) {
  process.exit(0);
}

const filePath = (input.tool_input && input.tool_input.file_path) || '';
if (!filePath) process.exit(0);

const normalized = filePath.replace(/\\/g, '/');
const ext = path.extname(filePath).toLowerCase();
const isPython = ext === '.py';
const isTypeScript = ext === '.ts' || ext === '.tsx';

// ── 1. Scope directory check ──
// Block edits outside project directory
const projectDir = path.resolve(__dirname, '../..');
if (!filePath.startsWith(projectDir)) {
  process.stderr.write(`BLOCKED: Edit outside project directory: ${filePath}\nFix: Only edit files within the project.\n`);
  process.exit(2);
}

// ── 2. Protect .env files ──
const basename = path.basename(filePath);
if (basename === '.env' || basename.endsWith('.env.local')) {
  process.stderr.write(`BLOCKED: Cannot modify ${basename} — environment files contain real secrets. Edit manually.\nFix: Edit .env.example instead for documentation, or edit .env manually outside Claude.\n`);
  process.exit(2);
}

// ── 3. Detect secrets ──
try {
  const content = fs.readFileSync(filePath, 'utf8');
  const patterns = [
    { name: 'OpenAI Key', regex: /sk-[A-Za-z0-9]{20,}/ },
    { name: 'AWS Key', regex: /AKIA[A-Z0-9]{16}/ },
    { name: 'Connection String', regex: /:\/\/[^\s:]+:[^\s@]+@/ },
  ];
  // Skip .env files (already blocked above) and lock files
  if (!basename.includes('.env') && !basename.endsWith('.lock')) {
    const found = [];
    for (const p of patterns) {
      const match = content.match(p.regex);
      if (match) {
        found.push(`  - ${p.name}: ${match[0].substring(0, 10)}...`);
      }
    }
    if (found.length > 0) {
      process.stderr.write(`BLOCKED: Potential secrets detected in ${filePath}:\n${found.join('\n')}\nFix: Move secrets to .env and reference via os.environ.get(). Never hardcode credentials.\n`);
      process.exit(2);
    }
  }
} catch (_) {
  // Can't read file, skip
}

// Skip remaining checks for non-code files
if (!isPython && !isTypeScript) {
  process.exit(0);
}

// ── 4. File length check ──
const SKIP_DIRS = new Set(['test', 'tests', '__tests__', 'migrations', 'config']);
const parts = normalized.split('/');
const inSkipDir = parts.some(p => SKIP_DIRS.has(p));
if (!inSkipDir && !normalized.endsWith('.d.ts')) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    const lineCount = content.endsWith('\n') ? lines.length - 1 : lines.length;
    if (lineCount >= 300) {
      process.stderr.write(`BLOCKED: ${filePath} is ${lineCount} lines (hard limit 300).\nFix: Split by responsibility into separate modules.\n`);
      process.exit(2);
    }
    if (lineCount > 200) {
      process.stderr.write(`WARNING: ${filePath} is ${lineCount} lines (recommended max 200).\n`);
    }
  } catch (_) {}
}

// ── 5. Function length check (Python) ──
if (isPython && !inSkipDir) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    let funcName = null;
    let funcStart = 0;
    const violations = [];
    for (let i = 0; i < lines.length; i++) {
      const match = lines[i].match(/^(\s*)(def |async def )(\w+)/);
      if (match) {
        if (funcName && (i - funcStart) > 50) {
          violations.push(`  ${funcName} (${i - funcStart} lines, starting line ${funcStart + 1})`);
        }
        funcName = match[3];
        funcStart = i;
      }
    }
    if (funcName && (lines.length - funcStart) > 50) {
      violations.push(`  ${funcName} (${lines.length - funcStart} lines, starting line ${funcStart + 1})`);
    }
    if (violations.length > 0) {
      process.stderr.write(`WARNING: Long functions in ${filePath} (limit 50 lines):\n${violations.join('\n')}\n`);
    }
  } catch (_) {}
}

// ── 6. Lint on save ──
if (isPython) {
  const backendIdx = normalized.indexOf('/backend/');
  const cwd = backendIdx !== -1 ? normalized.substring(0, backendIdx + '/backend'.length) : process.cwd();
  spawnSync('sh', ['-c', `uv run ruff check --fix "${filePath}" 2>&1 && uv run ruff format "${filePath}" 2>&1`], {
    encoding: 'utf8',
    shell: false,
    cwd,
    timeout: 10000,
  });
} else if (isTypeScript) {
  const frontendIdx = normalized.indexOf('/frontend/');
  const cwd = frontendIdx !== -1 ? normalized.substring(0, frontendIdx + '/frontend'.length) : process.cwd();
  spawnSync('sh', ['-c', `npx eslint --fix "${filePath}" 2>&1`], {
    encoding: 'utf8',
    shell: false,
    cwd,
    timeout: 10000,
  });
}

process.exit(0);
