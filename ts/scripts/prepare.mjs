/**
 * npm's `prepare` hook -- what makes a source dependency rebuild itself.
 *
 * npm runs `prepare` when it installs a package from a `file:` dependency, and
 * re-runs it on every subsequent `npm install`. That is the whole mechanism by
 * which a consumer that lists pssparser as an IVPM source dependency gets the
 * WebAssembly artifact rebuilt from the sources it just fetched: `ivpm update`
 * drives `npm install`, npm drives this, this drives cmake and tsc. There is
 * no build declaration anywhere in `ivpm.yaml`, and there should not be --
 * npm already had the hook.
 *
 * `prepare` deliberately does *not* run when npm installs from a published
 * registry tarball, so a consumer that takes `@psstools/pssparser` off npm
 * never reaches this file and needs no Emscripten toolchain. The two
 * consumption modes are the same package:
 *
 *   source  -- ivpm dependency, `type: { node: { subdir: ts } }`; builds here
 *   package -- `src: npm`; ships `dist/`, including the prebuilt .wasm
 *
 * Skipped when SKIP_PSSPARSER_PREPARE is set. That exists for the one case
 * the hook is actively unhelpful in: a CI job that has already built the
 * artifact in an earlier step and is running `npm install` only to get
 * devDependencies for the test run.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { rootDir, tsDir } from './ivpm-python.mjs';

if (process.env.SKIP_PSSPARSER_PREPARE) {
  console.log('prepare: skipped (SKIP_PSSPARSER_PREPARE is set)');
  process.exit(0);
}

// A published tarball has no `src/`, so there is nothing to build from and
// `dist/` is already the deliverable. npm should not run us here at all; the
// check costs one syscall and turns a confusing failure into a no-op if some
// future npm decides otherwise.
//
// For that to be true this file has to BE in the tarball, which is why
// `scripts` is listed in package.json's `files` alongside `dist`. npm invokes
// a `prepare` hook by path before anything in it can decline to run, so a
// manifest that declares one and ships no script fails the install outright
// with MODULE_NOT_FOUND -- the guard below would never be reached. Shipping
// the directory costs a few kilobytes and makes the no-op reachable.
if (!existsSync(join(tsDir, 'src', 'index.ts'))) {
  console.log('prepare: no sources present -- nothing to build');
  process.exit(0);
}

// Emscripten is the one dependency that cannot be made cheap, so say plainly
// what is missing and which dep-set carries it rather than letting cmake fail
// with a compiler-not-found several layers down.
if (!existsSync(join(rootDir, 'packages', 'emsdk', 'emscripten', 'emcc'))) {
  console.error(
    `prepare: no Emscripten toolchain at ${join(rootDir, 'packages', 'emsdk')}\n\n` +
      'Building pssparser from source needs it. A consumer that only wants to\n' +
      'use the parser should depend on the published @psstools/pssparser\n' +
      'package instead, which ships the prebuilt WebAssembly and needs no\n' +
      'toolchain. To build from source, name the dep-set that carries it:\n\n' +
      '    - name: pssparser\n' +
      '      url: https://github.com/psstools/pssparser.git\n' +
      '      dep-set: ts-build\n' +
      '      deps-mode: nested\n' +
      '      type: { node: { subdir: ts } }\n'
  );
  process.exit(1);
}

// Our own devDependencies -- `tsc`, above all -- have to be provisioned here.
// When this package is installed as a `file:` dependency npm links it and runs
// `prepare`, but it does *not* install the linked package's devDependencies:
// they are ours, not the consumer's. Without this the build reached the very
// last step and failed with `sh: 1: tsc: not found`.
//
// SKIP_PSSPARSER_PREPARE is what stops this recursing. `npm install` in our own
// directory is itself a trigger for `prepare`, so the child would re-enter this
// file, and so would its child.
const steps = [
  ['install', ['install', '--no-audit', '--no-fund']],
  ['generate', ['run', 'generate']],
  ['build', ['run', 'build']],
];

for (const [label, argv] of steps) {
  console.log(`prepare: npm ${argv.join(' ')}`);
  const r = spawnSync('npm', argv, {
    stdio: 'inherit',
    cwd: tsDir,
    env: { ...process.env, SKIP_PSSPARSER_PREPARE: '1' },
  });
  if (r.status !== 0) {
    console.error(`prepare: ${label} failed`);
    process.exit(r.status ?? 1);
  }
}
