# Rule files whose examples must pass

Site-style `pss-rules` files used to test the examples harness
(lint-core-plan.md C5.5). Every example here must pass, natively
(`tests/python/lintcore/test_examples.py`) and in the WebAssembly build
(`ts/test/lint-parity.test.ts`, from `ts/test/fixtures/lint-parity.json`).

Between them they cover what an example can say: `code:` and `files:`,
`// expect:` with and without `@ line:col`, `/* expect: */`, several IDs in
one comment, `expect: none`, unnamed examples, options at their defaults,
`report:`, `let:`, `define:`, and `match:` with `inside`/`not_inside`.

After changing a file here, run `npm run gen:lint-parity-fixture` in `ts/`.
