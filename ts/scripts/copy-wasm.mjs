/**
 * Copy the WASM build products into `dist/` after `tsc`.
 *
 * `tsc` compiles `.ts` and ignores everything else, so the emcc glue
 * (`pssparser.js`) and the binary (`pssparser.wasm`) would be missing from the
 * package that gets published. They are build products of a different
 * toolchain that happen to live under `src/`; this is the one line of the
 * build that knows that.
 */
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const tsDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const from = join(tsDir, 'src', 'wasm');
const to = join(tsDir, 'dist', 'wasm');

const artifacts = ['pssparser.js', 'pssparser.wasm'];

const missing = artifacts.filter((f) => !existsSync(join(from, f)));
if (missing.length) {
  console.error(
    `Missing WASM build products: ${missing.join(', ')}\n` +
      'Run `npm run gen:wasm` first.'
  );
  process.exit(1);
}

mkdirSync(to, { recursive: true });
for (const f of artifacts) {
  copyFileSync(join(from, f), join(to, f));
  console.log(`  ${f} -> dist/wasm/${f}`);
}
