/**
 * Run `astbuilder` from the IVPM-managed Python environment.
 *
 *   node scripts/astbuilder.mjs gen-ts -astdir ../ast -o src/ast/generated
 *
 * The npm scripts used to spell this `../packages/python/bin/astbuilder`,
 * which is right for a standalone checkout and wrong for a nested source
 * dependency -- see `ivpm-python.mjs`. One indirection so both layouts work
 * and the resolution rule has a single home.
 */
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { requireVenvBin, rootDir, tsDir } from './ivpm-python.mjs';

const exe = join(requireVenvBin(), 'astbuilder');
const r = spawnSync(exe, process.argv.slice(2), { stdio: 'inherit', cwd: tsDir });

if (r.error && r.error.code === 'ENOENT') {
  console.error(
    `${exe} does not exist.\n` +
      'The environment was found but astbuilder is not installed in it. The\n' +
      'wasm/TypeScript build needs a pyastbuilder providing `gen-ts`,\n' +
      '`gen-wasm` and `gen-census`; re-run `ivpm update -d ts-build`.\n'
  );
  process.exit(1);
}
process.exit(r.status ?? 1);
