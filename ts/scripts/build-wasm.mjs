/**
 * Drive the Emscripten build from npm.
 *
 *   npm run gen:wasm
 *
 * A wrapper, not a build system: everything it knows is in
 * `wasm/CMakeLists.txt`. It exists so `npm run generate` is one command for a
 * TypeScript developer who should not have to learn the CMake invocation, and
 * so the "you have not fetched emsdk" case produces an instruction rather than
 * a compiler-not-found error.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const tsDir = resolve(here, '..');
const root = resolve(tsDir, '..');
const buildDir = join(root, 'build-wasm');
const emsdk = join(root, 'packages', 'emsdk');

if (!existsSync(join(emsdk, 'emscripten', 'emcc'))) {
  console.error(
    `No Emscripten toolchain at ${emsdk}.\n` +
      'The wasm build is a separate ivpm dep-set, because 300 MB is not a cost\n' +
      'a developer building only the Python extension should pay. `ts-build`\n' +
      'is that toolchain plus everything else this build needs:\n\n' +
      '    ivpm update -d ts-build\n'
  );
  process.exit(1);
}

// One bash -lc rather than execFile: `wasm-env.sh` sets PATH, EM_CONFIG and
// EM_CACHE for the whole toolchain, and `emcmake` is itself a script that
// re-execs cmake. Reproducing that setup in JavaScript would be a second copy
// of it to keep in step.
const script = [
  `set -e`,
  `cd ${JSON.stringify(root)}`,
  `source scripts/wasm-env.sh`,
  `emcmake cmake -S wasm -B ${JSON.stringify(buildDir)} -DCMAKE_BUILD_TYPE=Release`,
  `cmake --build ${JSON.stringify(buildDir)} -j`,
].join('\n');

const r = spawnSync('bash', ['-c', script], { stdio: 'inherit' });
process.exit(r.status ?? 1);
