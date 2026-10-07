import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

// Regression guard for Dependabot alert 47 on `source-map-js` (ADE-64): the transitive dependency (reached through
// postcss, css-tree and @tailwindcss/node, which all allow ^1.2.1) must resolve to the patched release, 1.2.2, or above.
// Dependabot cannot resolve this one itself, so the fix is a lockfile-only `pnpm update source-map-js --lockfile-only`.
const MINIMUM_PATCHED = '1.2.2';

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

describe('source-map-js is on a patched release', () => {
  it('compares versions correctly', () => {
    expect(atLeast('1.2.2', MINIMUM_PATCHED)).toBe(true);
    expect(atLeast('1.10.0', MINIMUM_PATCHED)).toBe(true);
    expect(atLeast('1.2.1', MINIMUM_PATCHED)).toBe(false);
    expect(atLeast('1.0.9', MINIMUM_PATCHED)).toBe(false);
  });

  it('pnpm-lock.yaml resolves only patched source-map-js versions', () => {
    const lock = readFileSync(path.join(frontendDir, 'pnpm-lock.yaml'), 'utf8');
    const resolved = [...lock.matchAll(/^ {2}source-map-js@(\d+\.\d+\.\d+)[:(]/gm)].map((m) => m[1]);
    expect(resolved.length).toBeGreaterThan(0);
    for (const version of resolved) {
      expect(atLeast(version, MINIMUM_PATCHED)).toBe(true);
    }
  });

  it('pnpm-lock.yaml points every parent at a patched source-map-js', () => {
    const lock = readFileSync(path.join(frontendDir, 'pnpm-lock.yaml'), 'utf8');
    const used = [...lock.matchAll(/^ {6}source-map-js: (\d+\.\d+\.\d+)$/gm)].map((m) => m[1]);
    expect(used.length).toBeGreaterThan(0);
    for (const version of used) {
      expect(atLeast(version, MINIMUM_PATCHED)).toBe(true);
    }
  });

  it('the source-map-js installed for postcss is at or above the patched version', () => {
    const fromFrontend = createRequire(path.join(frontendDir, 'package.json'));
    const fromPostcss = createRequire(fromFrontend.resolve('postcss/package.json'));
    const installed = fromPostcss('source-map-js/package.json').version as string;
    expect(atLeast(installed, MINIMUM_PATCHED)).toBe(true);
  });
});
