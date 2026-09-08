/**
 * Locate the IVPM-managed Python environment.
 *
 * A standalone checkout finds `<pssparser>/packages/python` immediately and
 * nothing here matters. It matters when pssparser is a *source dependency* of
 * something else: a consumer that declares `deps-mode: nested` gets
 * pssparser's directory dependencies under `<pssparser>/packages/`, but ivpm's
 * Python handler is root-scoped, so the venv astbuilder was installed into
 * belongs to the consuming workspace and sits several levels up.
 *
 * So walk up the enclosing deps-dirs. `wasm/CMakeLists.txt` does the same
 * search in CMake, for the same reason -- it cannot call into this file, and
 * duplicating six lines beat inventing a channel between them.
 */
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const tsDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const rootDir = resolve(tsDir, '..');

/** The venv's bin/ directory, or null when no environment is found. */
export function findVenvBin(start = rootDir) {
  // `PSSPARSER_PYTHON_BIN` is the escape hatch for a layout that is neither a
  // standalone checkout nor a nested dependency.
  const override = process.env.PSSPARSER_PYTHON_BIN;
  if (override) return existsSync(override) ? override : null;

  let dir = start;
  for (let i = 0; i < 8; i++) {
    const bin = join(dir, 'packages', 'python', 'bin');
    if (existsSync(join(bin, 'python'))) return bin;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

/** The venv bin/, or exit(1) with an instruction rather than ENOENT. */
export function requireVenvBin() {
  const bin = findVenvBin();
  if (bin) return bin;
  console.error(
    `No IVPM Python environment found at or above ${rootDir}.\n` +
      'The TypeScript build runs `astbuilder` out of it. Fetch it with:\n\n' +
      '    ivpm update -d ts-build\n\n' +
      'or point PSSPARSER_PYTHON_BIN at an environment that has astbuilder.\n'
  );
  process.exit(1);
}
