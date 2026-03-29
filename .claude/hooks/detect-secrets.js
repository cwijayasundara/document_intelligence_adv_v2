#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const input = JSON.parse(fs.readFileSync('/dev/stdin', 'utf8'));
const filePath = input.tool_input && input.tool_input.file_path;

if (!filePath) {
  process.exit(0);
}

const resolvedFilePath = path.resolve(filePath);

// Skip by file extension
const ext = path.extname(filePath).toLowerCase();
if (ext === '.md') {
  process.exit(0);
}

// Skip .env.example
const basename = path.basename(filePath);
if (basename === '.env.example') {
  process.exit(0);
}

// Skip files in hooks/, evals/, or templates/ directories
const normalised = resolvedFilePath.replace(/\\/g, '/');
if (
  normalised.includes('/hooks/') ||
  normalised.includes('/evals/') ||
  normalised.includes('/templates/')
) {
  process.exit(0);
}

// Read the file content
let content;
try {
  content = fs.readFileSync(resolvedFilePath, 'utf8');
} catch (err) {
  // If the file cannot be read (e.g. does not exist yet), allow the operation
  process.exit(0);
}

// Secret patterns: [label, RegExp] — all use the global flag for matchAll
const patterns = [
  ['AWS Access Key',     /AKIA[0-9A-Z]{16}/g],
  ['GitHub Token',       /gh[pousr]_[^\s"'`]{1,}/g],
  ['Anthropic Key',      /sk-ant-[^\s"'`]{1,}/g],
  ['OpenAI Key',         /sk-[a-zA-Z0-9]{20,}/g],
  ['Slack Token',        /xox[baprs]-[^\s"'`]{1,}/g],
  ['Private Key Block',  /-----BEGIN .* PRIVATE KEY-----/g],
  ['Connection String',  /:\/\/[^:]+:[^@]+@/g],
  ['SSN',                /\b\d{3}-\d{2}-\d{4}\b/g],
];

/**
 * Redact a matched value: show the first 10 characters followed by "..."
 */
function redact(value) {
  if (value.length <= 10) {
    return value.substring(0, 4) + '...';
  }
  return value.substring(0, 10) + '...';
}

const findings = [];

for (const [label, pattern] of patterns) {
  const matches = Array.from(content.matchAll(pattern));
  for (const match of matches) {
    findings.push({ label, value: redact(match[0]) });
  }
}

if (findings.length > 0) {
  const lines = [`BLOCKED: Potential secrets detected in ${filePath}:`];
  for (const { label, value } of findings) {
    lines.push(`  - ${label}: ${value}`);
  }
  lines.push('Fix: Move secrets to .env and reference via os.environ.get(). Never hardcode credentials.');
  process.stderr.write(lines.join('\n') + '\n');
  process.exit(2);
}

process.exit(0);
