#######################
Diagnostics JSON schema
#######################

``pssparser --format json`` (or ``--json``) writes one JSON document to
stdout.  This page describes schema ``pssparser-diagnostics/2``.

Every key of version 1 -- the shape before the ``schema`` key existed -- is
still present with the same meaning, so a version-1 consumer keeps working.
New keys may be added within a schema version; a key is removed or changes
meaning only with a new version.

Document
========

.. code-block:: json

   {
     "schema": "pssparser-diagnostics/2",
     "diagnostics": [],
     "summary": {"errors": 0, "warnings": 1, "notes": 0, "hints": 0, "files": 1},
     "waived": [],
     "statistics": [],
     "stats": {}
   }

``schema``
   Always ``"pssparser-diagnostics/2"``.  *New in 2.*
``diagnostics``
   Every diagnostic reported, in report order, including ``hint``
   diagnostics that text output hides.
``summary``
   Counts by severity after the warning policy ran: ``errors``,
   ``warnings``, ``notes`` (``info``; *new in 2*), ``hints`` (*new in 2*),
   and ``files`` (files processed).
``waived``
   Present when a source waiver covered at least one diagnostic: those
   diagnostics, each with a ``waiver`` key (below).  They are not in
   ``diagnostics`` and not in the ``summary`` counts, so a consumer that
   ignores this key sees what the exit code saw.  See :doc:`waivers`.
``statistics``
   Present with ``--statistics``: one object per code, most frequent first,
   with ``code``, ``count``, ``name`` and ``tier`` (empty strings when the
   code has none).  *New in 2.*
``stats``
   Present with ``--stats``; see *Run statistics* in :doc:`cli`.

Diagnostic
==========

.. code-block:: json

   {
     "file": "model.pss",
     "line": 4,
     "col": 3,
     "end_col": 9,
     "severity": "warning",
     "message": "'import lib::*;' follows a declaration; ...",
     "code": "LINT402",
     "rule": "import-after-declaration",
     "tier": "style",
     "family": "import",
     "related": [{"file": "model.pss", "line": 3, "col": 3, "label": "first declaration here"}]
   }

``file``, ``line``, ``col``
   Where the diagnostic points; 1-based.  A diagnostic about the tool itself
   (an extension that failed to load) has ``file`` ``"<pssparser>"`` and
   ``line``/``col`` 0.
``end_col``
   Exclusive end column of the underlined span, when known.
``severity``
   ``error``, ``warning``, ``info`` or ``hint``, after ``[severity]``
   overrides and the warning policy.
``original_severity``
   Present only on a diagnostic ``-Werror`` promoted: what it was before.
``message``
   The message text.  A checker's message starts with the ID in brackets, ``[PRC001]``.
``code``
   The marker ID, when the diagnostic has one.  Old IDs never appear here:
   a code that moved namespace is always reported under its current ID.
``rule``, ``tier``, ``family``, ``lrm``
   The rule's name, tier, family and LRM clause references, for codes that
   declare them.  *New in 2.*
``suggestion``
   A one-line replacement for the flagged text, when there is one.
``fix``
   A machine-applicable edit: ``file``, ``line``, ``col``, ``end_line``,
   ``end_col`` and ``replacement``.  Its span is the edit's, not the
   diagnostic's.
``related``
   Secondary locations, each with ``file``, ``line``, ``col`` and
   ``label``.
``waiver``
   Only in the ``waived`` array: the waiver that covered it, with ``form``
   (``"annotation"`` or ``"pragma"``), ``id`` as written, ``file``,
   ``line``, ``col`` (where the waiver is written) and ``reason``.
