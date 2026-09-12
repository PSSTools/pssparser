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
import { availableParallelism, totalmem } from 'node:os';
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

/**
 * How many compilers to run at once.
 *
 * THIS USED TO BE A BARE `-j`, WHICH IS NOT "a sensible default" -- cmake
 * passes it straight through, and `make -j` with no count means UNLIMITED:
 * make starts every target whose prerequisites are ready, all at once. Against
 * this build that is upwards of two hundred concurrent `emcc` processes, each
 * one a clang with its own resident set.
 *
 * On a workstation with cores and memory to spare it looks like a fast build.
 * On a 4-core, 16 GB CI runner it exhausts memory and the kernel's OOM killer
 * takes whatever it likes -- including the runner agent, which is why the
 * failure did not read as a build failure at all. Both attempts at the 3.1.2
 * release died this way, at 30% and at 99%, reported as:
 *
 *     ##[error]The runner has received a shutdown signal.
 *
 * with `gmake: *** Terminated` beside it and no compiler diagnostic anywhere.
 * The differing percentages are the tell: a deterministic compile error stops
 * in the same place twice, memory pressure stops wherever the allocations
 * happened to land.
 *
 * `availableParallelism()` respects cgroup CPU limits, so it reports the
 * container's share rather than the host's on a CI runner. It is capped
 * against memory besides -- emcc peaks well above a gigabyte on the larger
 * translation units here, and cores are not the scarce resource.
 */
function jobs() {
  const override = process.env.PSSPARSER_BUILD_JOBS;
  if (override) {
    const n = Number.parseInt(override, 10);
    if (Number.isInteger(n) && n > 0) return n;
    console.error(`Ignoring PSSPARSER_BUILD_JOBS=${override}: not a positive integer`);
  }
  const byCpu = availableParallelism();
  const byMemory = Math.max(1, Math.floor(totalmem() / (2 * 1024 * 1024 * 1024)));
  return Math.max(1, Math.min(byCpu, byMemory));
}

const j = jobs();
console.log(`gen:wasm: building with -j${j}`);

// One bash -lc rather than execFile: `wasm-env.sh` sets PATH, EM_CONFIG and
// EM_CACHE for the whole toolchain, and `emcmake` is itself a script that
// re-execs cmake. Reproducing that setup in JavaScript would be a second copy
// of it to keep in step.
const script = [
  `set -e`,
  `cd ${JSON.stringify(root)}`,
  `source scripts/wasm-env.sh`,
  `emcmake cmake -S wasm -B ${JSON.stringify(buildDir)} -DCMAKE_BUILD_TYPE=Release`,
  `cmake --build ${JSON.stringify(buildDir)} -j ${j}`,
].join('\n');

const r = spawnSync('bash', ['-c', script], { stdio: 'inherit' });
process.exit(r.status ?? 1);
