/**
 * Running lint rules (lint-core-plan.md C5.4): the request and result of
 * `Parser.runLint()`, and their conversion to and from the core's JSON
 * (`ILintEngine::run`). The rules run in the C++ core, so the editor and the
 * CLI give the same findings.
 */

import { resolveMarker, sortMarkers, type Marker, type RawMarker } from './Marker.js';

/** What to run. Every field is optional. */
export interface LintRequest {
  /**
   * The rule IDs to run, in any order; the rest are never evaluated.
   * Omitted: every loaded rule. Selection by profile, tier or namespace is
   * the host's job; this takes its result.
   */
  enabled?: string[];
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
  /** Request entries that were ignored: an unknown ID or option, a value of
   *  the wrong type. */
  problems: string[];
}

interface RawLintResult {
  ok: boolean;
  error?: string;
  markers?: RawMarker[];
  stats?: LintRuleStats[];
  problems?: string[];
}

/** The core's request JSON. */
export function lintRequestJson(req: LintRequest, gateErrors: number): string {
  const out: Record<string, unknown> = { gate_errors: req.gateErrors ?? gateErrors };
  if (req.enabled !== undefined) {
    out.enabled = req.enabled;
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
    problems: raw.problems ?? [],
  };
}
