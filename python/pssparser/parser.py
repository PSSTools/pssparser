from io import StringIO
from typing import Dict, List, Tuple, TextIO

class ParseException(Exception):
    def __init__(self, message, markers=None):
        super().__init__(message)
        self.markers = markers or []

class Parser(object):

    def __init__(self):
        import pssparser.core as zspp
        import pssparser.ast as zsp_ast
        self.ast_f = zsp_ast.Factory.inst()
        self.parser_f = zspp.Factory.inst()
        self._root = None
        self._filenames : Dict[int,str] = {}
        self._files : List[zsp_ast.GlobalScope] = []
        self._enable_profiling = False
        self._last_builder = None
        self._markers = []
        #: fileid -> path, snapshotted by link() before it clears its state.
        self._file_map : Dict[int,str] = {}
        pass

    def parse(self, files : List[str]) -> bool:
        import pssparser.core as zspp
        marker_l = self.parser_f.mkMarkerCollector()
        builder = self.parser_f.mkAstBuilder(marker_l)
        
        if self._enable_profiling:
            builder.setEnableProfile(True)

        file_id = 0
        if len(self._files) == 0:
            stdlib = self.ast_f.mkGlobalScope(len(self._files))
            self.parser_f.loadStandardLibrary(builder, stdlib)
            self._files.append(stdlib)

        for f in files:
            id = len(self._files)
            self._filenames[id] = f
            with open(f, "r") as fp:
                ast = self.ast_f.mkGlobalScope(id)
                builder.build(ast, fp)
            
            if marker_l.hasSeverity(zspp.MarkerSeverityE.Error):
                self._markers = self._collectMarkers(marker_l)
                err = self._mkErrorMessage(marker_l)
                raise ParseException(err, self._markers)

            self._files.append(ast)

        self._last_builder = builder
        self._markers = self._collectMarkers(marker_l)

        return True

    def parses(self, files : List[Tuple[str, str]]) -> bool:
        import pssparser.core as zspp
        marker_l = self.parser_f.mkMarkerCollector()
        builder = self.parser_f.mkAstBuilder(marker_l)
        
        if self._enable_profiling:
            builder.setEnableProfile(True)

        if len(self._files) == 0:
            stdlib = self.ast_f.mkGlobalScope(len(self._files))
            self.parser_f.loadStandardLibrary(builder, stdlib)
            self._files.append(stdlib)

        for fname,fstr in files:
            id = len(self._files)
            self._filenames[id] = fname
            ast = self.ast_f.mkGlobalScope(id)
            builder.build(ast, StringIO(fstr))
            
            if marker_l.hasSeverity(zspp.MarkerSeverityE.Error):
                self._markers = self._collectMarkers(marker_l)
                err = self._mkErrorMessage(marker_l)
                raise ParseException(err, self._markers)

            self._files.append(ast)

        self._last_builder = builder
        self._markers = self._collectMarkers(marker_l)

        return True
    
    def enable_profiling(self, enable: bool = True):
        """Enable or disable ANTLR profiling for subsequent parse operations."""
        # Profiling must be enabled before creating builder
        # This is a placeholder - will take effect on next parse
        self._enable_profiling = enable

    def get_profile_info(self):
        """Get profiling information from the last parse operation.
        
        Returns ParseProfileInfo object with decision-level and aggregate metrics,
        or None if profiling was not enabled or no parse has been performed.
        """
        if hasattr(self, '_last_builder') and self._last_builder is not None:
            return self._last_builder.getProfileInfo()
        return None
    
    def link(self) -> 'zsp_ast.RootSymbolScope':
        import pssparser.core as zspp
        linker = self.parser_f.mkAstLinker()
        marker_l = self.parser_f.mkMarkerCollector()

        ret = linker.link(marker_l, self._files)

        if marker_l.hasSeverity(zspp.MarkerSeverityE.Error):
            self._markers.extend(self._collectMarkers(marker_l))
            err = self._mkErrorMessage(marker_l)
            raise ParseException(err, self._markers)

        # Snapshot the fileid -> path mapping before clearing. Consumers that
        # run *after* linking -- checker plug-ins in particular -- still need
        # to resolve a fileid to a path, and clearing without a snapshot is
        # why CheckContext.file_map arrived empty.
        #
        # Only the mapping is retained, never the GlobalScope objects. The
        # linker takes ownership of them (TaskBuildSymbolTree pushes each into
        # root->getUnits() as an owning pointer), so a Python wrapper kept
        # past this point is a second owner of the same memory and will fault.
        # That is why _files is cleared here; it is deliberate, not an
        # oversight. Reach the per-file scopes through the linked root
        # instead -- see user_units().
        self._file_map = dict(self._filenames)
        self._root = ret

        self._filenames.clear()
        self._files.clear()

        return ret

    @property
    def file_map(self) -> Dict[int, str]:
        """Map fileid -> source path for the user-supplied files.

        Populated by :meth:`link` and valid afterwards. Built-in and library
        units are excluded: they carry fileid 0 or -1 and have no user path.
        """
        return dict(self._file_map)

    def user_units(self) -> List['zsp_ast.GlobalScope']:
        """The GlobalScope of each user-supplied file, in parse order.

        Read from the linked root, which owns the units after :meth:`link`.
        Built-in and standard-library units are filtered out by fileid.

        Returns an empty list before :meth:`link` has run.
        """
        if self._root is None:
            return []
        out = []
        for i in range(self._root.numUnits()):
            u = self._root.getUnit(i)
            if u is not None and u.getFileid() in self._file_map:
                out.append(u)
        return out


    def _mkErrorMessage(self, marker_l) -> str:
        import pssparser.core as zspp
        prefix = {
            zspp.MarkerSeverityE.Error : "Error: ",
            zspp.MarkerSeverityE.Warn : "Warning: ",
            zspp.MarkerSeverityE.Info : "Info: ",
            zspp.MarkerSeverityE.Hint : "Hint: ",
        }
        msg = ""
        for i in range(marker_l.numMarkers()):
            marker = marker_l.getMarker(i)
            loc = marker.loc()
            marker_m = "%s%s %s:%d:%d" % (
                prefix[int(marker.severity())],
                marker.msg(),
                self._filenames.get(loc.file, "<unknown>"),
                loc.line,
                loc.pos+1)
            msg += marker_m + "\n"

        return msg

    def _collectMarkers(self, marker_l) -> list:
        """Collect structured marker data from a MarkerCollector."""
        import pssparser.core as zspp
        severity_names = {
            int(zspp.MarkerSeverityE.Error): "error",
            int(zspp.MarkerSeverityE.Warn): "warning",
            int(zspp.MarkerSeverityE.Info): "info",
            int(zspp.MarkerSeverityE.Hint): "hint",
        }
        result = []
        for i in range(marker_l.numMarkers()):
            m = marker_l.getMarker(i)
            loc = m.loc()
            filename = self._filenames.get(loc.file, "<unknown>")
            result.append({
                "severity": severity_names.get(int(m.severity()), "unknown"),
                "message": m.msg(),
                "file": filename,
                "line": loc.line,
                "col": loc.pos + 1,
            })
        return result

    @property
    def markers(self) -> list:
        """Structured list of markers from the last parse/link operation.
        
        Each marker is a dict with keys:
            severity: "error", "warning", "info", or "hint"
            message: Human-readable error message
            file: Source filename
            line: Line number (1-based)
            col: Column number (1-based)
        """
        return list(self._markers)

    @property
    def root(self) -> 'zsp_ast.RootSymbolScope':
        return self._root
