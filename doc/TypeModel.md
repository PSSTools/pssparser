
- Packages are not represented hierarchically
-> All package content from a CU is aggregated
- All types (eg action, component) are identified by fully-qualified name

- All declared types are registered with the CU (TypeDecl)
- Type references are stored locally (no global declaration?)

= Name resolution
- Resolve imports first (need to ensure we know where to look)
- After that, doesn't matter
