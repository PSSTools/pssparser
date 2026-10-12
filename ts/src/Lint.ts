/**
 * Running lint rules (lint-core-plan.md C5.4): the request and result of
 * `Parser.runLint()`, and their conversion to and from the core's JSON
 * (`ILintEngine::run`). The rules run in the C++ core, so the editor and the
 * CLI give the same findings.
 */

import { resolveMarker, sortMarkers, type Marker, type RawMarker } from './Marker.js';

/** One `[[lint.overrides]]` table: settings for the files its globs match. */
export interface LintOverride {
  /**
   * Globs relative to the base directory: `*` and `?` stay within a
   * directory, `**` crosses them; a glob without `/` matches a file or
   * directory name at any depth. A glob that matches a directory takes
   * everything under it.
   */
  files: string[];
  profile?: string;
  select?: string[];
  ignore?: string[];
  /** Option values by rule name or ID. */
  rule?: Record<string, Record<string, string | number | boolean | string[]>>;
}

/**
 * A rule selection (lint-core-plan.md C7.1): the configuration's TOML as
 * parsed, with its keys as written there. The core resolves it, the same
 * code the CLI runs: profiles, selectors and their precedence, the
 * overrides, the command line's layer, `[severity]` and `-W` groups.
 */
export interface LintSelection {
  lint?: {
    profile?: string;
    select?: string[];
    ignore?: string[];
    'rules-version'?: string;
    rule?: Record<string, Record<string, string | number | boolean | string[]>>;
    overrides?: LintOverride[];
  };
  /** A layer over `lint.select` / `lint.ignore`: `--select` and `--ignore`. */
  command_line?: { select?: string[]; ignore?: string[] };
  /** `[severity]`: selector to `error`, `warning`, `info`, `hint` or `off`. */
  severity?: Record<string, string>;
  /**
   * `[warnings]`: `error = true` is `-Werror`, a list is `-Werror=` each
   * selector (`"info"` promotes `info` diagnostics); `no-error` exempts;
   * `none = true` is `--no-warnings`. Applied by `Parser.lint()`.
   */
  warnings?: { error?: string[] | boolean; 'no-error'?: string[]; none?: boolean };
  /** The directory the override globs are relative to: the configuration's. */
  base_dir?: string;
}

/** A selection problem: a selector or rule the catalogue does not know. */
export interface SelectionError {
  /** `lint.select`, `lint.overrides[0].ignore`, `--select`, `request`, ... */
  key: string;
  text: string;
  message: string;
}

/** The rules of the files one combination of overrides matches. */
export interface SelectionGroup {
  /** Indexes into `lint.overrides`; group 0 has none. */
  overrides: number[];
  profile: string;
  enabled: string[];
  /** The enabled rules a selector names by ID, name, ID band or namespace. */
  explicit: string[];
  /** Rules the `rules-version` pin keeps out of the profile. */
  held_back: string[];
  options: Record<string, Record<string, unknown>>;
}

/** `Parser.resolveSelection()`'s answer. */
export interface SelectionResult {
  errors: SelectionError[];
  lint_ids: string[];
  /** Group 0 is the files no override matches. */
  groups: SelectionGroup[];
  /** Each requested path, as the globs saw it, and its group. */
  paths: Array<{ path: string; rel: string; group: number }>;
  /** `[severity]` expanded to IDs, with the key that set each. */
  severity: Record<string, { severity: string; key: string }>;
  warnings: {
    error: string[];
    /** `error = true`. */
    error_all: boolean;
    error_info: boolean;
    spelling: Record<string, string>;
    no_error: string[];
    /** `none = true`. */
    none: boolean;
  };
}

/**
 * One of the host's own markers, for selection and waivers (C7.1): what a
 * selector may name besides the loaded rules and the core's markers, which
 * the engine knows already (C7.3). Only `id` is required.
 */
export interface HostMarker {
  id: string;
  name?: string;
  /** A lint tier, `tool`, or empty for an LRM marker. */
  tier?: string;
  family?: string;
  since?: string;
  /** `active` (the default), `deprecated` or `retired`. */
  status?: string;
  /** Empty: the tier's. */
  severity?: string;
  aliases?: string[];
  replaced_by?: string[];
  default_enabled?: boolean;
  /** In the `minimal` profile. */
  minimal?: boolean;
}

/** One entry of the marker catalogue (`Parser.catalog()`, C7.3). */
export interface CatalogMarker {
  id: string;
  name: string;
  /** A lint tier, `tool`, or empty for an LRM marker. */
  tier: string;
  family: string;
  /** `YYYY.N`, the rule-set version the rule entered; may be empty. */
  since: string;
  /** `active`, `deprecated`, `retired` or `reserved`. */
  status: string;
  /** The effective default severity: the marker's, else its tier's. */
  severity: string;
  /** Former IDs, still accepted by selectors and waivers. */
  aliases: string[];
  replaced_by: string[];
  default_enabled: boolean;
  /** In the `minimal` profile. */
  minimal: boolean;
  /** One line. Empty for a host marker. */
  summary: string;
  /** The documentation (reStructuredText for a core marker, Markdown for a
   *  rule's `doc`). Empty for a host marker. */
  detail: string;
  /** LRM references. */
  lrm: string[];
  /** The documentation page for the ID, for an editor's `codeDescription`. */
  doc_url: string;
  /** Where the entry comes from: the core's embedded catalogue, a loaded
   *  rule file, or `setHostMarkers()` alone. */
  source: 'core' | 'rules' | 'host';
}

/** The lint taxonomy, as `checkers/taxonomy.py` defines it. */
export interface CatalogTaxonomy {
  /** Each tier with its default severity, in documentation order. */
  tiers: [string, string][];
  families: string[];
  profiles: string[];
  default_profile: string;
  /** The tiers each profile enables (`minimal` lists rules, not tiers). */
  profile_tiers: Record<string, string[]>;
  /** The documentation URL template; `{id}` is the lower-cased ID. */
  doc_url: string;
}

/** The marker catalogue (`Parser.catalog()`, lint-core-plan.md C7.3). */
export interface Catalog {
  schema: 'pssparser-catalog/1';
  taxonomy: CatalogTaxonomy;
  /** The core's markers in registry order, then the host's, then the loaded
   *  rules'. */
  markers: CatalogMarker[];
}

/**
 * A source waiver (lint-core-plan.md C7.2; `docs/waivers.rst`): a
 * `// pssparser waive` comment or a `@lint_pkg::waive` annotation.
 */
export interface Waiver {
  form: 'pragma' | 'annotation';
  file: string;
  /** Where the waiver is written, 1-based. */
  line: number;
  col: number;
  /** As written: IDs, rule names or any selector. */
  selectors: string[];
  reason: string;
  /** The span it covers, `[line, col]`, `end` exclusive; 2^30 is "to the end". */
  start: [number, number];
  end: [number, number];
}

/** A diagnostic as `Parser.applyWaivers()` reads it. */
export interface WaiverDiagnostic {
  code?: string | null;
  file: string;
  line: number;
  col: number;
}

/** A waiver hygiene marker: `PSSP202`-`PSSP205`, or `PSSP004` for an old ID. */
export interface WaiverMarker {
  severity: string;
  message: string;
  file: string;
  line: number;
  col: number;
  code: string;
  extent: number;
  related: unknown[];
}

/** `Parser.applyWaivers()`'s answer. */
export interface WaiverResult {
  /** Indexes of the diagnostics to report. */
  kept: number[];
  /** `[diagnostic, waiver]` index pairs. */
  waived: Array<[number, number]>;
  /** The waivers, with the IDs each resolved to and how many it waived. */
  waivers: Array<Waiver & { ids: string[]; used: number }>;
  /** Sorted by file, line, column and code. */
  markers: WaiverMarker[];
}

/** What to run. Every field is optional. */
export interface LintRequest {
  /**
   * The rule IDs to run, in any order; the rest are never evaluated.
   * Omitted: every loaded rule. Or give `selection` instead.
   */
  enabled?: string[];
  /**
   * The configuration to select by, in place of `enabled` and `options`
   * (C7.1): each file runs, and reports, the rules its path gets, with its
   * options. Its `base_dir` defaults to `baseDir`.
   */
  selection?: LintSelection;
  /** Option values by rule ID, overriding each option's `default:`. */
  options?: Record<string, Record<string, string | number | boolean | string[]>>;
  /** The evaluation-step budget per rule per file. Omitted: 10^6. */
  maxSteps?: number;
  /**
   * The lint gate: the number of errors parse, link and the semantic checks
   * reported. Above 0, no rule runs and the one `PSSP230` marker ("lint
   * skipped: N errors") is returned, when any rule was enabled. Omitted: the
   * error markers this `Parser` holds.
   */
  gateErrors?: number;
  /**
   * The directory `file_of()` gives paths relative to: the configuration's,
   * as the CLI uses. Give it and the file names in the same form (both
   * absolute paths, or both URIs' paths). Omitted: paths as the files were
   * named to `parse()`.
   */
  baseDir?: string;
}

/** What one rule did in the run. */
export interface LintRuleStats {
  id: string;
  matches: number;
  findings: number;
  /** Evaluation steps, across files. */
  steps: number;
  /** Evaluation time in nanoseconds, across files. */
  ns: number;
  /** Failures (`PSSP220`, `PSSP221`): at most one per file. */
  errors: number;
}

export interface LintResult {
  /**
   * The findings (`code` is the rule's ID), the rule failures (`PSSP220`,
   * `PSSP221`) or the gate's `PSSP230`, sorted by file, line and column.
   * Messages carry no `[ID]` prefix, as the core's markers do not.
   */
  markers: Marker[];
  /** The enabled rules, in load order. */
  stats: LintRuleStats[];
  /**
   * Nanoseconds spent building the library's indexes (parent links, symbol
   * occurrences): the run's cost, in no rule's `ns`.
   */
  indexNs: number;
  /** Request entries that were ignored: an unknown ID or option, a value of
   *  the wrong type. */
  problems: string[];
}

interface RawLintResult {
  ok: boolean;
  error?: string;
  markers?: RawMarker[];
  stats?: LintRuleStats[];
  index_ns?: number;
  problems?: string[];
}

/** The core's request JSON. */
export function lintRequestJson(
  req: LintRequest,
  gateErrors: number,
  files: ReadonlyMap<number, string> = new Map(),
): string {
  const out: Record<string, unknown> = { gate_errors: req.gateErrors ?? gateErrors };
  // The parser's names for its files, for file_of() (C6.9).
  out.files = Object.fromEntries([...files].map(([id, name]) => [String(id), name]));
  if (req.baseDir !== undefined) {
    out.base_dir = req.baseDir;
  }
  if (req.enabled !== undefined) {
    out.enabled = req.enabled;
  }
  if (req.selection !== undefined) {
    out.selection = req.selection;
  }
  if (req.options !== undefined) {
    out.options = req.options;
  }
  if (req.maxSteps !== undefined) {
    out.max_steps = req.maxSteps;
  }
  return JSON.stringify(out);
}

/**
 * The file of a marker that belongs to no source file (the gate's
 * `PSSP230`), as the Python CLI names it (`extension.NO_FILE`); its line and
 * column are 0.
 */
export const NO_FILE = '<pssparser>';

function resolve(m: RawMarker, files: ReadonlyMap<number, string>): Marker {
  if (m.fileid < 0 && m.line < 1) {
    return { ...resolveMarker(m, files), file: NO_FILE, line: 0, col: 0, extent: 0 };
  }
  return resolveMarker(m, files);
}

/** The core's result JSON, with markers resolved against `files`. */
export function parseLintResult(json: string, files: ReadonlyMap<number, string>): LintResult {
  const raw = JSON.parse(json) as RawLintResult;
  if (!raw.ok) {
    // Only a malformed request gets here, and lintRequestJson() builds it.
    throw new Error(`runLint: ${raw.error ?? 'bad request'}`);
  }
  return {
    markers: sortMarkers((raw.markers ?? []).map((m) => resolve(m, files))),
    stats: raw.stats ?? [],
    indexNs: raw.index_ns ?? 0,
    problems: raw.problems ?? [],
  };
}

/** What `Parser.lint()` does. Every field is optional. */
export interface LintOptions {
  /**
   * The configuration: `.pssparser.toml` as parsed, with its keys as written
   * there (`[lint]`, `[severity]`, `[warnings]`). Omitted: the default
   * profile, no severity changes, no `-W` policy.
   */
  selection?: LintSelection;
  /**
   * The sources whose `// pssparser waive` comments and `@lint_pkg::waive`
   * annotations apply, by the names they were parsed under: usually the
   * same list given to `parseSources()`. Omitted: no waivers.
   */
  sources?: readonly { name: string; content: string }[];
  /** `false` turns source waivers off, as `[waivers] source = false` does. */
  waivers?: boolean;
  /** The evaluation-step budget per rule per file. Omitted: 10^6. */
  maxSteps?: number;
  /** The directory `file_of()` is relative to; see `LintRequest.baseDir`. */
  baseDir?: string;
}

/** A diagnostic as `Parser.lint()` reports it: what the CLI prints. */
export interface LintDiagnostic extends Marker {
  /** Before `-Werror` promoted it to `error`. */
  originalSeverity?: string;
  /** The flag that promoted it, as written: `-Werror`, `-Werror=style`. */
  werror?: string;
  /** For a waived diagnostic, the waiver that covered it. */
  waiver?: Waiver;
}

/** `Parser.lint()`'s answer. */
export interface LintReport {
  /**
   * The parse and link markers and the rules' findings, after selection,
   * `[severity]`, waivers and the `-W` policy, with the waiver hygiene
   * markers (`PSSP202`-`PSSP205`, `PSSP004`); sorted by file, line and
   * column. Rule messages carry no `[ID]` prefix.
   */
  diagnostics: LintDiagnostic[];
  /** The diagnostics a waiver covered, each with its `waiver`. */
  waived: LintDiagnostic[];
  /** The waivers, with the IDs each resolved to and how many it waived. */
  waivers: Array<Waiver & { ids: string[]; used: number }>;
  /** What each enabled rule did. */
  stats: LintRuleStats[];
  /** Nanoseconds spent building indexes, in no rule's `ns` (`LintResult.indexNs`). */
  indexNs: number;
  /** Request or configuration entries that were ignored. */
  problems: string[];
}
