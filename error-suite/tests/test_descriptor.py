"""Descriptor loading and its strictness."""
from __future__ import annotations

import sys

import pytest

from pss_errsuite.descriptor import DescriptorError, load_descriptor

MINIMAL = """
[tool]
name = "t"
[invoke]
argv = ["t", "{files}"]
[output]
kind = "regex"
pattern = '^(?P<message>.*)$'
"""

_ARGV_LINE = 'argv = ["t", "{files}"]'


def with_invoke(line, *, argv=_ARGV_LINE):
    """MINIMAL with `line` added to [invoke] -- appending to MINIMAL would land
    it in [output], which is the last section."""
    return MINIMAL.replace(_ARGV_LINE, f"{argv}\n{line}")


@pytest.fixture
def load(tmp_path):
    def _load(text, name="t.toml"):
        p = tmp_path / name
        p.write_text(text)
        return load_descriptor(p, tmp_path)
    return _load


def test_minimal_descriptor(load):
    d = load(MINIMAL)
    assert d.name == "t"
    assert d.argv == ["t", "{files}"]
    assert d.capabilities.multifile is True
    assert d.capabilities.max_errors is False


def test_unknown_section_is_rejected(load):
    with pytest.raises(DescriptorError, match=r"unknown section \[extras\]"):
        load(MINIMAL + "\n[extras]\nx = 1\n")


def test_unknown_key_is_rejected(load):
    """A typo'd capability declaration shows up later as a mysterious pile of
    `skipped` cases, so it is rejected at load time instead."""
    with pytest.raises(DescriptorError, match="unknown key"):
        load('[tool]\nname = "t"\n[invoke]\nargv = ["t", "{files}"]\n'
             "[capabilities]\nmultifle = true\n")


def test_argv_must_mention_files(load):
    with pytest.raises(DescriptorError, match=r"\{files\}"):
        load(MINIMAL.replace('argv = ["t", "{files}"]', 'argv = ["t"]'))


def test_file_argv_is_loaded_and_defaults_to_a_bare_path(load):
    assert load(MINIMAL).file_argv == ["{file}"]
    d = load(with_invoke('file_argv = ["-pss", "{file}"]'))
    assert d.file_argv == ["-pss", "{file}"]


def test_file_argv_that_never_names_the_file_is_rejected(load):
    """Without `{file}` the tool is handed flags and no input at all, and every
    case comes back empty -- which classifies as `missed` and reads as a broken
    tool rather than a broken descriptor."""
    with pytest.raises(DescriptorError, match=r"file_argv must contain"):
        load(with_invoke('file_argv = ["-pss"]'))


def test_file_argv_using_the_plural_placeholder_is_rejected(load):
    with pytest.raises(DescriptorError, match=r"it describes a single file"):
        load(with_invoke('file_argv = ["-pss", "{files}"]'))


def test_the_singular_placeholder_in_argv_is_rejected(load):
    """`{file}` belongs to file_argv; in argv nothing expands it and it would
    reach the tool as a literal."""
    with pytest.raises(DescriptorError, match=r"argv uses '\{file\}'"):
        load(with_invoke('file_argv = ["-pss", "{file}"]',
                         argv='argv = ["t", "{file}", "{files}"]'))


def test_file_argv_needs_a_standalone_files_element_to_expand_at(load):
    """The embedded form (`--src={files}`) is single-file by construction, so
    there is no group for file_argv to repeat."""
    with pytest.raises(DescriptorError, match="standalone"):
        load(with_invoke('file_argv = ["-pss", "{file}"]',
                         argv='argv = ["t", "--src={files}"]'))


def test_a_subprocess_tool_with_no_output_section_is_rejected(load):
    """Defaulting would be silent ruin: no way to read diagnostics means every
    case is `missed`, which reads as a terrible tool rather than a typo."""
    with pytest.raises(DescriptorError, match=r"\[output\] section is required"):
        load('[tool]\nname = "t"\n[invoke]\nargv = ["t", "{files}"]\n')


def test_regex_output_needs_a_message_group(load):
    with pytest.raises(DescriptorError, match="message"):
        load('[tool]\nname="t"\n[invoke]\nargv=["t","{files}"]\n'
             "[output]\nkind='regex'\npattern='^(?P<file>.*)$'\n")


def test_bad_regex_is_reported_as_a_descriptor_error(load):
    with pytest.raises(DescriptorError, match=r"\[output\] pattern"):
        load('[tool]\nname="t"\n[invoke]\nargv=["t","{files}"]\n'
             "[output]\nkind='regex'\npattern='(?P<message>'\n")


def test_declaring_max_errors_without_a_flag_is_rejected(load):
    """Otherwise the runner has no way to set the cap and every volume case
    silently measures the tool's default cap instead of the tool."""
    with pytest.raises(DescriptorError, match="max_errors_argv is empty"):
        load(MINIMAL + "\n[capabilities]\nmax_errors = true\n")


def test_placeholders_expand(load, tmp_path):
    d = load(MINIMAL.replace('argv = ["t", "{files}"]',
                             'argv = ["{python}", "{suite_root}/x.py", "{files}"]'))
    assert d.argv[0] == sys.executable
    assert d.argv[1] == str(tmp_path / "x.py")


def test_missing_pss_is_recorded_as_assumed(load):
    """Nothing verifies a declared version, so an *absent* one must fail in the
    tool's disfavour rather than silently skipping the newer cases."""
    d = load(MINIMAL)
    assert d.pss is None and d.pss_assumed is True
    declared = load(MINIMAL.replace('name = "t"', 'name = "t"\npss = "3.0"'))
    assert declared.pss == "3.0" and declared.pss_assumed is False


def test_shipped_descriptors_all_load(suite_root):
    for path in sorted((suite_root / "tools").glob("*.toml")):
        assert load_descriptor(path, suite_root).name
