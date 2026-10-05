import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

// Regression guard for Dependabot alerts on `next` (ADE-45 to ADE-50): every place that decides which
// Next.js version runs must be at or above the highest patched release, 16.3.6.
const MINIMUM_PATCHED = '16.3.6';

const frontendDir = path.resolve(__dirname, '..');

function parse(version: string): [number, number, number] {
  const match = /^(\d+)\.(\d+)\.(\d+)/.exec(version);
  if (!match) throw new Error(`not a plain semver version: ${version}`);
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function atLeast(version: string, minimum: string): boolean {
  const a = parse(version);
  const b = parse(minimum);
  for (let i = 0; i < 3; i += 1) {
    if (a[i] !== b[i]) return a[i] > b[i];
  }
  return true;
}

describe('next is on a patched release', () => {
  it('compares versions correctly', () => {
    expect(atLeast('16.3.6', MINIMUM_PATCHED)).toBe(true);
    expect(atLeast('16.10.0', MINIMUM_PATCHED)).toBe(true);
    expect(atLeast('16.3.5', MINIMUM_PATCHED)).toBe(false);
    expect(atLeast('15.9.9', MINIMUM_PATCHED)).toBe(false);
  });

  it('package.json pins next at or above the patched version', () => {
    const pkg = JSON.parse(readFileSync(path.join(frontendDir, 'package.json'), 'utf8'));
    expect(atLeast(pkg.dependencies.next, MINIMUM_PATCHED)).toBe(true);
  });

  it('pnpm-lock.yaml resolves only patched next versions', () => {
    const lock = readFileSync(path.join(frontendDir, 'pnpm-lock.yaml'), 'utf8');
    const resolved = [...lock.matchAll(/^ {2}next@(\d+\.\d+\.\d+)[:(]/gm)].map((m) => m[1]);
    expect(resolved.length).toBeGreaterThan(0);
    for (const version of resolved) {
      expect(atLeast(version, MINIMUM_PATCHED)).toBe(true);
    }
  });

  it('the installed next package is at or above the patched version', () => {
    const require = createRequire(path.join(frontendDir, 'package.json'));
    const installed = require('next/package.json').version as string;
    expect(atLeast(installed, MINIMUM_PATCHED)).toBe(true);
  });
});
