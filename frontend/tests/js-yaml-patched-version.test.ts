import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

// Regression guard for Dependabot alert 8 on `js-yaml` (ADE-77): `maxTotalMergeKeys` does not limit CPU use for empty merge
// sources in `>= 4.0.0, < 4.3.2`. js-yaml is a transitive dependency (eslint -> @eslint/eslintrc, which allows ^4.3.0), so the
// lockfile is what pins it; the fix is a lockfile-only `pnpm update js-yaml --lockfile-only`.
const MINIMUM_PATCHED = '4.3.2';

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

describe('js-yaml is on a patched release', () => {
  it('compares versions correctly', () => {
    expect(atLeast('4.3.2', MINIMUM_PATCHED)).toBe(true);
    expect(atLeast('4.10.0', MINIMUM_PATCHED)).toBe(true);
    expect(atLeast('4.3.1', MINIMUM_PATCHED)).toBe(false);
    expect(atLeast('4.0.0', MINIMUM_PATCHED)).toBe(false);
  });

  it('pnpm-lock.yaml resolves only patched js-yaml versions', () => {
    const lock = readFileSync(path.join(frontendDir, 'pnpm-lock.yaml'), 'utf8');
    const resolved = [...lock.matchAll(/^ {2}js-yaml@(\d+\.\d+\.\d+)[:(]/gm)].map((m) => m[1]);
    expect(resolved.length).toBeGreaterThan(0);
    for (const version of resolved) {
      expect(atLeast(version, MINIMUM_PATCHED), `js-yaml@${version} is below ${MINIMUM_PATCHED}`).toBe(true);
    }
  });

  it('pnpm-lock.yaml points every parent at a patched js-yaml', () => {
    const lock = readFileSync(path.join(frontendDir, 'pnpm-lock.yaml'), 'utf8');
    const used = [...lock.matchAll(/^ {6}js-yaml: (\d+\.\d+\.\d+)$/gm)].map((m) => m[1]);
    expect(used.length).toBeGreaterThan(0);
    for (const version of used) {
      expect(atLeast(version, MINIMUM_PATCHED), `edge to js-yaml ${version} is below ${MINIMUM_PATCHED}`).toBe(true);
    }
  });
});
