#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');

const MAX_LINES = 50;

// Get leading whitespace length (spaces; tabs count as 1)
function indentLen(line) {
  let count = 0;
  for (const ch of line) {
    if (ch === ' ' || ch === '\t') count++;
    else break;
  }
  return count;
}

function checkPython(lines, filePath) {
  const warnings = [];
  const funcDef = /^(\s*)(async\s+)?def\s+(\w+)\s*\(/;
  const funcStack = []; // { name, startLine, indent }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const match = line.match(funcDef);

    if (match) {
      const indent = indentLen(line);
      const name = match[3];

      // Pop any functions whose indent >= current (they ended before this line)
      while (funcStack.length > 0 && funcStack[funcStack.length - 1].indent >= indent) {
        const ended = funcStack.pop();
        const length = i - ended.startLine; // lines from def to just before current
        if (length > MAX_LINES) {
          warnings.push(
            `WARNING: Function ${ended.name} in ${filePath}:${ended.startLine + 1} is ${length} lines (max ${MAX_LINES}).\nFix: Decompose into named sub-functions. Each should be testable in isolation.`
          );
        }
      }

      funcStack.push({ name, startLine: i, indent });
    }
  }

  // Close remaining functions at EOF
  const totalLines = lines.length;
  while (funcStack.length > 0) {
    const ended = funcStack.pop();
    const length = totalLines - ended.startLine;
    if (length > MAX_LINES) {
      warnings.push(
        `WARNING: Function ${ended.name} in ${filePath}:${ended.startLine + 1} is ${length} lines (max ${MAX_LINES}).`
      );
    }
  }

  return warnings;
}

function checkTypeScript(lines, filePath) {
  const warnings = [];
  // Named function declarations: function foo(
  const namedFuncRe = /\bfunction\s+(\w+)\s*[(<]/;
  // Arrow functions assigned to const: const foo = (  or  const foo = async (
  const arrowFuncRe = /\bconst\s+(\w+)\s*=\s*(async\s*)?\(/;

  const funcStack = []; // { name, startLine, braceDepth }
  let braceDepth = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check for function start before counting braces on this line
    const namedMatch = line.match(namedFuncRe);
    const arrowMatch = line.match(arrowFuncRe);

    const funcName = (namedMatch && namedMatch[1]) || (arrowMatch && arrowMatch[1]) || null;

    // Count braces on this line
    let openCount = 0;
    let closeCount = 0;
    for (const ch of line) {
      if (ch === '{') openCount++;
      else if (ch === '}') closeCount++;
    }

    if (funcName) {
      // Record entry at the brace depth AFTER opens on this line
      funcStack.push({ name: funcName, startLine: i, braceDepth: braceDepth + openCount });
    }

    braceDepth += openCount - closeCount;

    // Pop functions whose body braceDepth has been closed
    while (funcStack.length > 0) {
      const top = funcStack[funcStack.length - 1];
      // The function body started at top.braceDepth; it ends when braceDepth drops below that
      if (braceDepth < top.braceDepth) {
        const ended = funcStack.pop();
        const length = i - ended.startLine + 1;
        if (length > MAX_LINES) {
          warnings.push(
            `WARNING: Function ${ended.name} in ${filePath}:${ended.startLine + 1} is ${length} lines (max ${MAX_LINES}).\nFix: Decompose into named sub-functions. Each should be testable in isolation.`
          );
        }
      } else {
        break;
      }
    }
  }

  // Close remaining at EOF
  const totalLines = lines.length;
  while (funcStack.length > 0) {
    const ended = funcStack.pop();
    const length = totalLines - ended.startLine;
    if (length > MAX_LINES) {
      warnings.push(
        `WARNING: Function ${ended.name} in ${filePath}:${ended.startLine + 1} is ${length} lines (max ${MAX_LINES}).`
      );
    }
  }

  return warnings;
}

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

  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (_) {
    process.exit(0);
  }

  const lines = content.split('\n');
  let warnings = [];

  if (isPython) {
    warnings = checkPython(lines, filePath);
  } else {
    warnings = checkTypeScript(lines, filePath);
  }

  for (const w of warnings) {
    process.stderr.write(w + '\n');
  }
} catch (err) {
  process.stderr.write(`check-function-length.js error: ${err.message}\n`);
}

process.exit(0);
