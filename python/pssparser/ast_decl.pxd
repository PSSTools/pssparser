# cython: language_level=3
from enum import IntEnum
from libcpp.cast cimport dynamic_cast
from libcpp.cast cimport reinterpret_cast
from libcpp.cast cimport static_cast
from libcpp.string cimport string as      std_string
from libcpp.map cimport map as            std_map
from libcpp.unordered_map cimport unordered_map as  std_unordered_map
from libcpp.memory cimport unique_ptr, shared_ptr
from libcpp.vector cimport vector as std_vector
from libcpp.utility cimport pair as  std_pair
from libcpp cimport bool as          bool
cimport cpython.ref as cpy_ref
from cython.operator cimport dereference

cdef extern from "pssp/ast/impl/UP.h" namespace "pssp::ast":
    cpdef cppclass UP[T](unique_ptr[T]):
        UP()
        UP(T *, bool)
        T *get()

ctypedef char                 int8_t
ctypedef unsigned char        uint8_t
ctypedef short                int16_t
ctypedef unsigned short       uint16_t
ctypedef int                  int32_t
ctypedef unsigned int         uint32_t
ctypedef long long            int64_t
ctypedef unsigned long long   uint64_t

ctypedef ISymbolImportSpec *ISymbolImportSpecP
ctypedef UP[ISymbolImportSpec] ISymbolImportSpecUP
ctypedef IAssocData *IAssocDataP
ctypedef UP[IAssocData] IAssocDataUP
ctypedef ISymbolRefPath *ISymbolRefPathP
ctypedef UP[ISymbolRefPath] ISymbolRefPathUP
ctypedef ITemplateParamDeclList *ITemplateParamDeclListP
ctypedef UP[ITemplateParamDeclList] ITemplateParamDeclListUP
ctypedef IActivityMatchChoice *IActivityMatchChoiceP
ctypedef UP[IActivityMatchChoice] IActivityMatchChoiceUP
ctypedef ITemplateParamValue *ITemplateParamValueP
ctypedef UP[ITemplateParamValue] ITemplateParamValueUP
ctypedef ITemplateParamValueList *ITemplateParamValueListP
ctypedef UP[ITemplateParamValueList] ITemplateParamValueListUP
ctypedef IExpr *IExprP
ctypedef UP[IExpr] IExprUP
ctypedef IScopeChild *IScopeChildP
ctypedef UP[IScopeChild] IScopeChildUP
ctypedef IActivitySelectBranch *IActivitySelectBranchP
ctypedef UP[IActivitySelectBranch] IActivitySelectBranchUP
ctypedef IExprAggrMapElem *IExprAggrMapElemP
ctypedef UP[IExprAggrMapElem] IExprAggrMapElemUP
ctypedef IExprAggrStructElem *IExprAggrStructElemP
ctypedef UP[IExprAggrStructElem] IExprAggrStructElemUP
ctypedef IActionFieldInitializer *IActionFieldInitializerP
ctypedef UP[IActionFieldInitializer] IActionFieldInitializerUP
ctypedef IFunctionDefinition *IFunctionDefinitionP
ctypedef UP[IFunctionDefinition] IFunctionDefinitionUP
ctypedef IFunctionImport *IFunctionImportP
ctypedef UP[IFunctionImport] IFunctionImportUP
ctypedef IFunctionParamDecl *IFunctionParamDeclP
ctypedef UP[IFunctionParamDecl] IFunctionParamDeclUP
ctypedef ITypedefDeclaration *ITypedefDeclarationP
ctypedef UP[ITypedefDeclaration] ITypedefDeclarationUP
ctypedef IGenericConstraintDeclValue *IGenericConstraintDeclValueP
ctypedef UP[IGenericConstraintDeclValue] IGenericConstraintDeclValueUP
ctypedef IActivityJoinSpec *IActivityJoinSpecP
ctypedef UP[IActivityJoinSpec] IActivityJoinSpecUP
ctypedef IGenericConstraintParam *IGenericConstraintParamP
ctypedef UP[IGenericConstraintParam] IGenericConstraintParamUP
ctypedef IMethodParameterList *IMethodParameterListP
ctypedef UP[IMethodParameterList] IMethodParameterListUP
ctypedef IActivitySchedulingConstraint *IActivitySchedulingConstraintP
ctypedef UP[IActivitySchedulingConstraint] IActivitySchedulingConstraintUP
ctypedef IMonitorActivityStmt *IMonitorActivityStmtP
ctypedef UP[IMonitorActivityStmt] IMonitorActivityStmtUP
ctypedef IActivityStmt *IActivityStmtP
ctypedef UP[IActivityStmt] IActivityStmtUP
ctypedef INamedScopeChild *INamedScopeChildP
ctypedef UP[INamedScopeChild] INamedScopeChildUP
ctypedef IOverrideStmt *IOverrideStmtP
ctypedef UP[IOverrideStmt] IOverrideStmtUP
ctypedef IAnnotation *IAnnotationP
ctypedef UP[IAnnotation] IAnnotationUP
ctypedef IPackageImportStmt *IPackageImportStmtP
ctypedef UP[IPackageImportStmt] IPackageImportStmtUP
ctypedef IAnnotationParam *IAnnotationParamP
ctypedef UP[IAnnotationParam] IAnnotationParamUP
ctypedef IComment *ICommentP
ctypedef UP[IComment] ICommentUP
ctypedef IComponentBind *IComponentBindP
ctypedef UP[IComponentBind] IComponentBindUP
ctypedef IComponentBindTarget *IComponentBindTargetP
ctypedef UP[IComponentBindTarget] IComponentBindTargetUP
ctypedef IComponentPathElem *IComponentPathElemP
ctypedef UP[IComponentPathElem] IComponentPathElemUP
ctypedef IProceduralStmtIfClause *IProceduralStmtIfClauseP
ctypedef UP[IProceduralStmtIfClause] IProceduralStmtIfClauseUP
ctypedef IConstraintStmt *IConstraintStmtP
ctypedef UP[IConstraintStmt] IConstraintStmtUP
ctypedef IPyImportFromStmt *IPyImportFromStmtP
ctypedef UP[IPyImportFromStmt] IPyImportFromStmtUP
ctypedef IPyImportStmt *IPyImportStmtP
ctypedef UP[IPyImportStmt] IPyImportStmtUP
ctypedef IScope *IScopeP
ctypedef UP[IScope] IScopeUP
ctypedef ICoverStmtReference *ICoverStmtReferenceP
ctypedef UP[ICoverStmtReference] ICoverStmtReferenceUP
ctypedef IScopeChildRef *IScopeChildRefP
ctypedef UP[IScopeChildRef] IScopeChildRefUP
ctypedef ISymbolChild *ISymbolChildP
ctypedef UP[ISymbolChild] ISymbolChildUP
ctypedef ICovergroupOption *ICovergroupOptionP
ctypedef UP[ICovergroupOption] ICovergroupOptionUP
ctypedef ICovergroupPortmap *ICovergroupPortmapP
ctypedef UP[ICovergroupPortmap] ICovergroupPortmapUP
ctypedef IDataType *IDataTypeP
ctypedef UP[IDataType] IDataTypeUP
ctypedef ITargetTemplateFunction *ITargetTemplateFunctionP
ctypedef UP[ITargetTemplateFunction] ITargetTemplateFunctionUP
ctypedef IDistItem *IDistItemP
ctypedef UP[IDistItem] IDistItemUP
ctypedef IDistWeight *IDistWeightP
ctypedef UP[IDistWeight] IDistWeightUP
ctypedef ITemplateParamDecl *ITemplateParamDeclP
ctypedef UP[ITemplateParamDecl] ITemplateParamDeclUP
ctypedef IExecBlockTag *IExecBlockTagP
ctypedef UP[IExecBlockTag] IExecBlockTagUP
ctypedef ITemplateParamExprValue *ITemplateParamExprValueP
ctypedef UP[ITemplateParamExprValue] ITemplateParamExprValueUP
ctypedef IExecStmt *IExecStmtP
ctypedef UP[IExecStmt] IExecStmtUP
ctypedef IExecTargetTemplateBlock *IExecTargetTemplateBlockP
ctypedef UP[IExecTargetTemplateBlock] IExecTargetTemplateBlockUP
ctypedef IExportAction *IExportActionP
ctypedef UP[IExportAction] IExportActionUP
ctypedef IExportFunction *IExportFunctionP
ctypedef UP[IExportFunction] IExportFunctionUP
ctypedef ITemplateParamTypeValue *ITemplateParamTypeValueP
ctypedef UP[ITemplateParamTypeValue] ITemplateParamTypeValueUP
ctypedef IExprAggrLiteral *IExprAggrLiteralP
ctypedef UP[IExprAggrLiteral] IExprAggrLiteralUP
ctypedef ITypeIdentifier *ITypeIdentifierP
ctypedef UP[ITypeIdentifier] ITypeIdentifierUP
ctypedef ITypeIdentifierElem *ITypeIdentifierElemP
ctypedef UP[ITypeIdentifierElem] ITypeIdentifierElemUP
ctypedef IExprBin *IExprBinP
ctypedef UP[IExprBin] IExprBinUP
ctypedef IExprBitSlice *IExprBitSliceP
ctypedef UP[IExprBitSlice] IExprBitSliceUP
ctypedef IExprBool *IExprBoolP
ctypedef UP[IExprBool] IExprBoolUP
ctypedef IExprCast *IExprCastP
ctypedef UP[IExprCast] IExprCastUP
ctypedef IExprCompileHas *IExprCompileHasP
ctypedef UP[IExprCompileHas] IExprCompileHasUP
ctypedef IExprCond *IExprCondP
ctypedef UP[IExprCond] IExprCondUP
ctypedef IExprDomainOpenRangeList *IExprDomainOpenRangeListP
ctypedef UP[IExprDomainOpenRangeList] IExprDomainOpenRangeListUP
ctypedef IExprDomainOpenRangeValue *IExprDomainOpenRangeValueP
ctypedef UP[IExprDomainOpenRangeValue] IExprDomainOpenRangeValueUP
ctypedef IExprFloatLiteral *IExprFloatLiteralP
ctypedef UP[IExprFloatLiteral] IExprFloatLiteralUP
ctypedef IExprHierarchicalId *IExprHierarchicalIdP
ctypedef UP[IExprHierarchicalId] IExprHierarchicalIdUP
ctypedef IExprId *IExprIdP
ctypedef UP[IExprId] IExprIdUP
ctypedef IExprIn *IExprInP
ctypedef UP[IExprIn] IExprInUP
ctypedef IExprMemberPathElem *IExprMemberPathElemP
ctypedef UP[IExprMemberPathElem] IExprMemberPathElemUP
ctypedef IExprNull *IExprNullP
ctypedef UP[IExprNull] IExprNullUP
ctypedef IExprNumber *IExprNumberP
ctypedef UP[IExprNumber] IExprNumberUP
ctypedef IExprOpenRangeList *IExprOpenRangeListP
ctypedef UP[IExprOpenRangeList] IExprOpenRangeListUP
ctypedef IExprOpenRangeValue *IExprOpenRangeValueP
ctypedef UP[IExprOpenRangeValue] IExprOpenRangeValueUP
ctypedef IExprRefPath *IExprRefPathP
ctypedef UP[IExprRefPath] IExprRefPathUP
ctypedef IExprSliceRange *IExprSliceRangeP
ctypedef UP[IExprSliceRange] IExprSliceRangeUP
ctypedef IExprString *IExprStringP
ctypedef UP[IExprString] IExprStringUP
ctypedef IExprUnary *IExprUnaryP
ctypedef UP[IExprUnary] IExprUnaryUP
ctypedef IExtendEnum *IExtendEnumP
ctypedef UP[IExtendEnum] IExtendEnumUP
ctypedef IActionHandleField *IActionHandleFieldP
ctypedef UP[IActionHandleField] IActionHandleFieldUP
ctypedef IActivityBindStmt *IActivityBindStmtP
ctypedef UP[IActivityBindStmt] IActivityBindStmtUP
ctypedef IActivityConstraint *IActivityConstraintP
ctypedef UP[IActivityConstraint] IActivityConstraintUP
ctypedef IActivityJoinSpecBranch *IActivityJoinSpecBranchP
ctypedef UP[IActivityJoinSpecBranch] IActivityJoinSpecBranchUP
ctypedef IActivityJoinSpecFirst *IActivityJoinSpecFirstP
ctypedef UP[IActivityJoinSpecFirst] IActivityJoinSpecFirstUP
ctypedef IActivityJoinSpecNone *IActivityJoinSpecNoneP
ctypedef UP[IActivityJoinSpecNone] IActivityJoinSpecNoneUP
ctypedef IActivityJoinSpecSelect *IActivityJoinSpecSelectP
ctypedef UP[IActivityJoinSpecSelect] IActivityJoinSpecSelectUP
ctypedef IActivityLabeledStmt *IActivityLabeledStmtP
ctypedef UP[IActivityLabeledStmt] IActivityLabeledStmtUP
ctypedef IActivitySymbolCall *IActivitySymbolCallP
ctypedef UP[IActivitySymbolCall] IActivitySymbolCallUP
ctypedef IConstraintScope *IConstraintScopeP
ctypedef UP[IConstraintScope] IConstraintScopeUP
ctypedef IConstraintStmtDefault *IConstraintStmtDefaultP
ctypedef UP[IConstraintStmtDefault] IConstraintStmtDefaultUP
ctypedef IConstraintStmtDefaultDisable *IConstraintStmtDefaultDisableP
ctypedef UP[IConstraintStmtDefaultDisable] IConstraintStmtDefaultDisableUP
ctypedef IConstraintStmtDist *IConstraintStmtDistP
ctypedef UP[IConstraintStmtDist] IConstraintStmtDistUP
ctypedef IConstraintStmtExpr *IConstraintStmtExprP
ctypedef UP[IConstraintStmtExpr] IConstraintStmtExprUP
ctypedef IConstraintStmtField *IConstraintStmtFieldP
ctypedef UP[IConstraintStmtField] IConstraintStmtFieldUP
ctypedef IConstraintStmtIf *IConstraintStmtIfP
ctypedef UP[IConstraintStmtIf] IConstraintStmtIfUP
ctypedef IConstraintStmtSoft *IConstraintStmtSoftP
ctypedef UP[IConstraintStmtSoft] IConstraintStmtSoftUP
ctypedef IConstraintStmtUnique *IConstraintStmtUniqueP
ctypedef UP[IConstraintStmtUnique] IConstraintStmtUniqueUP
ctypedef ICoverStmtInline *ICoverStmtInlineP
ctypedef UP[ICoverStmtInline] ICoverStmtInlineUP
ctypedef ICovergroup *ICovergroupP
ctypedef UP[ICovergroup] ICovergroupUP
ctypedef ICovergroupCoverpoint *ICovergroupCoverpointP
ctypedef UP[ICovergroupCoverpoint] ICovergroupCoverpointUP
ctypedef ICovergroupCross *ICovergroupCrossP
ctypedef UP[ICovergroupCross] ICovergroupCrossUP
ctypedef ICovergroupCrossBins *ICovergroupCrossBinsP
ctypedef UP[ICovergroupCrossBins] ICovergroupCrossBinsUP
ctypedef ICovergroupInstantiation *ICovergroupInstantiationP
ctypedef UP[ICovergroupInstantiation] ICovergroupInstantiationUP
ctypedef ICoverpointBins *ICoverpointBinsP
ctypedef UP[ICoverpointBins] ICoverpointBinsUP
ctypedef IDataTypeBool *IDataTypeBoolP
ctypedef UP[IDataTypeBool] IDataTypeBoolUP
ctypedef IDataTypeChandle *IDataTypeChandleP
ctypedef UP[IDataTypeChandle] IDataTypeChandleUP
ctypedef IDataTypeEnum *IDataTypeEnumP
ctypedef UP[IDataTypeEnum] IDataTypeEnumUP
ctypedef IDataTypeFloat *IDataTypeFloatP
ctypedef UP[IDataTypeFloat] IDataTypeFloatUP
ctypedef IDataTypeInt *IDataTypeIntP
ctypedef UP[IDataTypeInt] IDataTypeIntUP
ctypedef IDataTypePyObj *IDataTypePyObjP
ctypedef UP[IDataTypePyObj] IDataTypePyObjUP
ctypedef IDataTypeRef *IDataTypeRefP
ctypedef UP[IDataTypeRef] IDataTypeRefUP
ctypedef IDataTypeString *IDataTypeStringP
ctypedef UP[IDataTypeString] IDataTypeStringUP
ctypedef IDataTypeUserDefined *IDataTypeUserDefinedP
ctypedef UP[IDataTypeUserDefined] IDataTypeUserDefinedUP
ctypedef IEnumDecl *IEnumDeclP
ctypedef UP[IEnumDecl] IEnumDeclUP
ctypedef IEnumItem *IEnumItemP
ctypedef UP[IEnumItem] IEnumItemUP
ctypedef IExprAggrEmpty *IExprAggrEmptyP
ctypedef UP[IExprAggrEmpty] IExprAggrEmptyUP
ctypedef IExprAggrList *IExprAggrListP
ctypedef UP[IExprAggrList] IExprAggrListUP
ctypedef IExprAggrMap *IExprAggrMapP
ctypedef UP[IExprAggrMap] IExprAggrMapUP
ctypedef IExprAggrStruct *IExprAggrStructP
ctypedef UP[IExprAggrStruct] IExprAggrStructUP
ctypedef IExprRefPathContext *IExprRefPathContextP
ctypedef UP[IExprRefPathContext] IExprRefPathContextUP
ctypedef IExprRefPathStatic *IExprRefPathStaticP
ctypedef UP[IExprRefPathStatic] IExprRefPathStaticUP
ctypedef IExprRefPathStaticRooted *IExprRefPathStaticRootedP
ctypedef UP[IExprRefPathStaticRooted] IExprRefPathStaticRootedUP
ctypedef IExprSignedNumber *IExprSignedNumberP
ctypedef UP[IExprSignedNumber] IExprSignedNumberUP
ctypedef IExprTemplateString *IExprTemplateStringP
ctypedef UP[IExprTemplateString] IExprTemplateStringUP
ctypedef IExprUnsignedNumber *IExprUnsignedNumberP
ctypedef UP[IExprUnsignedNumber] IExprUnsignedNumberUP
ctypedef IExtendType *IExtendTypeP
ctypedef UP[IExtendType] IExtendTypeUP
ctypedef IField *IFieldP
ctypedef UP[IField] IFieldUP
ctypedef IFieldClaim *IFieldClaimP
ctypedef UP[IFieldClaim] IFieldClaimUP
ctypedef IFieldCompRef *IFieldCompRefP
ctypedef UP[IFieldCompRef] IFieldCompRefUP
ctypedef IFieldPool *IFieldPoolP
ctypedef UP[IFieldPool] IFieldPoolUP
ctypedef IFieldRef *IFieldRefP
ctypedef UP[IFieldRef] IFieldRefUP
ctypedef IFunctionImportProto *IFunctionImportProtoP
ctypedef UP[IFunctionImportProto] IFunctionImportProtoUP
ctypedef IFunctionImportType *IFunctionImportTypeP
ctypedef UP[IFunctionImportType] IFunctionImportTypeUP
ctypedef IFunctionPrototype *IFunctionPrototypeP
ctypedef UP[IFunctionPrototype] IFunctionPrototypeUP
ctypedef IGlobalScope *IGlobalScopeP
ctypedef UP[IGlobalScope] IGlobalScopeUP
ctypedef IInstanceOverride *IInstanceOverrideP
ctypedef UP[IInstanceOverride] IInstanceOverrideUP
ctypedef IMonitorActivityLabeledStmt *IMonitorActivityLabeledStmtP
ctypedef UP[IMonitorActivityLabeledStmt] IMonitorActivityLabeledStmtUP
ctypedef IMonitorConstraint *IMonitorConstraintP
ctypedef UP[IMonitorConstraint] IMonitorConstraintUP
ctypedef INamedScope *INamedScopeP
ctypedef UP[INamedScope] INamedScopeUP
ctypedef IOverrideDecl *IOverrideDeclP
ctypedef UP[IOverrideDecl] IOverrideDeclUP
ctypedef IPackageScope *IPackageScopeP
ctypedef UP[IPackageScope] IPackageScopeUP
ctypedef IProceduralStmtAssignment *IProceduralStmtAssignmentP
ctypedef UP[IProceduralStmtAssignment] IProceduralStmtAssignmentUP
ctypedef IProceduralStmtBody *IProceduralStmtBodyP
ctypedef UP[IProceduralStmtBody] IProceduralStmtBodyUP
ctypedef IProceduralStmtBreak *IProceduralStmtBreakP
ctypedef UP[IProceduralStmtBreak] IProceduralStmtBreakUP
ctypedef IProceduralStmtContinue *IProceduralStmtContinueP
ctypedef UP[IProceduralStmtContinue] IProceduralStmtContinueUP
ctypedef IProceduralStmtDataDeclaration *IProceduralStmtDataDeclarationP
ctypedef UP[IProceduralStmtDataDeclaration] IProceduralStmtDataDeclarationUP
ctypedef IProceduralStmtExpr *IProceduralStmtExprP
ctypedef UP[IProceduralStmtExpr] IProceduralStmtExprUP
ctypedef IProceduralStmtIfElse *IProceduralStmtIfElseP
ctypedef UP[IProceduralStmtIfElse] IProceduralStmtIfElseUP
ctypedef IProceduralStmtMatch *IProceduralStmtMatchP
ctypedef UP[IProceduralStmtMatch] IProceduralStmtMatchUP
ctypedef IProceduralStmtMatchChoice *IProceduralStmtMatchChoiceP
ctypedef UP[IProceduralStmtMatchChoice] IProceduralStmtMatchChoiceUP
ctypedef IProceduralStmtRandomize *IProceduralStmtRandomizeP
ctypedef UP[IProceduralStmtRandomize] IProceduralStmtRandomizeUP
ctypedef IProceduralStmtReturn *IProceduralStmtReturnP
ctypedef UP[IProceduralStmtReturn] IProceduralStmtReturnUP
ctypedef IProceduralStmtSuper *IProceduralStmtSuperP
ctypedef UP[IProceduralStmtSuper] IProceduralStmtSuperUP
ctypedef IProceduralStmtYield *IProceduralStmtYieldP
ctypedef UP[IProceduralStmtYield] IProceduralStmtYieldUP
ctypedef ISymbolChildrenScope *ISymbolChildrenScopeP
ctypedef UP[ISymbolChildrenScope] ISymbolChildrenScopeUP
ctypedef ITemplateCategoryTypeParamDecl *ITemplateCategoryTypeParamDeclP
ctypedef UP[ITemplateCategoryTypeParamDecl] ITemplateCategoryTypeParamDeclUP
ctypedef ITemplateGenericTypeParamDecl *ITemplateGenericTypeParamDeclP
ctypedef UP[ITemplateGenericTypeParamDecl] ITemplateGenericTypeParamDeclUP
ctypedef ITemplateValueParamDecl *ITemplateValueParamDeclP
ctypedef UP[ITemplateValueParamDecl] ITemplateValueParamDeclUP
ctypedef ITypeOverride *ITypeOverrideP
ctypedef UP[ITypeOverride] ITypeOverrideUP
ctypedef IActivityActionHandleTraversal *IActivityActionHandleTraversalP
ctypedef UP[IActivityActionHandleTraversal] IActivityActionHandleTraversalUP
ctypedef IActivityActionTypeTraversal *IActivityActionTypeTraversalP
ctypedef UP[IActivityActionTypeTraversal] IActivityActionTypeTraversalUP
ctypedef IActivityAtomicBlock *IActivityAtomicBlockP
ctypedef UP[IActivityAtomicBlock] IActivityAtomicBlockUP
ctypedef IActivityForeach *IActivityForeachP
ctypedef UP[IActivityForeach] IActivityForeachUP
ctypedef IActivityIfElse *IActivityIfElseP
ctypedef UP[IActivityIfElse] IActivityIfElseUP
ctypedef IActivityMatch *IActivityMatchP
ctypedef UP[IActivityMatch] IActivityMatchUP
ctypedef IMonitorActivityEventually *IMonitorActivityEventuallyP
ctypedef UP[IMonitorActivityEventually] IMonitorActivityEventuallyUP
ctypedef IActivityRepeatCount *IActivityRepeatCountP
ctypedef UP[IActivityRepeatCount] IActivityRepeatCountUP
ctypedef IActivityRepeatWhile *IActivityRepeatWhileP
ctypedef UP[IActivityRepeatWhile] IActivityRepeatWhileUP
ctypedef IActivityReplicate *IActivityReplicateP
ctypedef UP[IActivityReplicate] IActivityReplicateUP
ctypedef IActivitySelect *IActivitySelectP
ctypedef UP[IActivitySelect] IActivitySelectUP
ctypedef IActivitySuper *IActivitySuperP
ctypedef UP[IActivitySuper] IActivitySuperUP
ctypedef IConstraintBlock *IConstraintBlockP
ctypedef UP[IConstraintBlock] IConstraintBlockUP
ctypedef IProceduralStmtRepeatWhile *IProceduralStmtRepeatWhileP
ctypedef UP[IProceduralStmtRepeatWhile] IProceduralStmtRepeatWhileUP
ctypedef IConstraintStmtForall *IConstraintStmtForallP
ctypedef UP[IConstraintStmtForall] IConstraintStmtForallUP
ctypedef IConstraintStmtForeach *IConstraintStmtForeachP
ctypedef UP[IConstraintStmtForeach] IConstraintStmtForeachUP
ctypedef IProceduralStmtWhile *IProceduralStmtWhileP
ctypedef UP[IProceduralStmtWhile] IProceduralStmtWhileUP
ctypedef IConstraintStmtImplication *IConstraintStmtImplicationP
ctypedef UP[IConstraintStmtImplication] IConstraintStmtImplicationUP
ctypedef ISymbolScope *ISymbolScopeP
ctypedef UP[ISymbolScope] ISymbolScopeUP
ctypedef ITypeScope *ITypeScopeP
ctypedef UP[ITypeScope] ITypeScopeUP
ctypedef IExprRefPathSuper *IExprRefPathSuperP
ctypedef UP[IExprRefPathSuper] IExprRefPathSuperUP
ctypedef IAction *IActionP
ctypedef UP[IAction] IActionUP
ctypedef IActivityDecl *IActivityDeclP
ctypedef UP[IActivityDecl] IActivityDeclUP
ctypedef IGenericConstraintDeclBool *IGenericConstraintDeclBoolP
ctypedef UP[IGenericConstraintDeclBool] IGenericConstraintDeclBoolUP
ctypedef IImportClass *IImportClassP
ctypedef UP[IImportClass] IImportClassUP
ctypedef IActivityLabeledScope *IActivityLabeledScopeP
ctypedef UP[IActivityLabeledScope] IActivityLabeledScopeUP
ctypedef IMonitor *IMonitorP
ctypedef UP[IMonitor] IMonitorUP
ctypedef IMonitorActivityDecl *IMonitorActivityDeclP
ctypedef UP[IMonitorActivityDecl] IMonitorActivityDeclUP
ctypedef IMonitorActivityLabeledScope *IMonitorActivityLabeledScopeP
ctypedef UP[IMonitorActivityLabeledScope] IMonitorActivityLabeledScopeUP
ctypedef IAnnotationDecl *IAnnotationDeclP
ctypedef UP[IAnnotationDecl] IAnnotationDeclUP
ctypedef IComponent *IComponentP
ctypedef UP[IComponent] IComponentUP
ctypedef IProceduralStmtSymbolBodyScope *IProceduralStmtSymbolBodyScopeP
ctypedef UP[IProceduralStmtSymbolBodyScope] IProceduralStmtSymbolBodyScopeUP
ctypedef IConstraintSymbolScope *IConstraintSymbolScopeP
ctypedef UP[IConstraintSymbolScope] IConstraintSymbolScopeUP
ctypedef IRootSymbolScope *IRootSymbolScopeP
ctypedef UP[IRootSymbolScope] IRootSymbolScopeUP
ctypedef IStruct *IStructP
ctypedef UP[IStruct] IStructUP
ctypedef ISymbolDeclaration *ISymbolDeclarationP
ctypedef UP[ISymbolDeclaration] ISymbolDeclarationUP
ctypedef ISymbolEnumScope *ISymbolEnumScopeP
ctypedef UP[ISymbolEnumScope] ISymbolEnumScopeUP
ctypedef ISymbolExtendScope *ISymbolExtendScopeP
ctypedef UP[ISymbolExtendScope] ISymbolExtendScopeUP
ctypedef ICovergroupType *ICovergroupTypeP
ctypedef UP[ICovergroupType] ICovergroupTypeUP
ctypedef ISymbolFunctionScope *ISymbolFunctionScopeP
ctypedef UP[ISymbolFunctionScope] ISymbolFunctionScopeUP
ctypedef ISymbolTypeScope *ISymbolTypeScopeP
ctypedef UP[ISymbolTypeScope] ISymbolTypeScopeUP
ctypedef ITemplateElem *ITemplateElemP
ctypedef UP[ITemplateElem] ITemplateElemUP
ctypedef IExecScope *IExecScopeP
ctypedef UP[IExecScope] IExecScopeUP
ctypedef ITemplateString *ITemplateStringP
ctypedef UP[ITemplateString] ITemplateStringUP
ctypedef ITemplateText *ITemplateTextP
ctypedef UP[ITemplateText] ITemplateTextUP
ctypedef ITemplateAssign *ITemplateAssignP
ctypedef UP[ITemplateAssign] ITemplateAssignUP
ctypedef IProceduralStmtForeach *IProceduralStmtForeachP
ctypedef UP[IProceduralStmtForeach] IProceduralStmtForeachUP
ctypedef ITemplateBlock *ITemplateBlockP
ctypedef UP[ITemplateBlock] ITemplateBlockUP
ctypedef ITemplateComment *ITemplateCommentP
ctypedef UP[ITemplateComment] ITemplateCommentUP
ctypedef ITemplateExpr *ITemplateExprP
ctypedef UP[ITemplateExpr] ITemplateExprUP
ctypedef IProceduralStmtRepeat *IProceduralStmtRepeatP
ctypedef UP[IProceduralStmtRepeat] IProceduralStmtRepeatUP
ctypedef ITemplateIf *ITemplateIfP
ctypedef UP[ITemplateIf] ITemplateIfUP
ctypedef IExecBlock *IExecBlockP
ctypedef UP[IExecBlock] IExecBlockUP
ctypedef IMonitorActivityConcat *IMonitorActivityConcatP
ctypedef UP[IMonitorActivityConcat] IMonitorActivityConcatUP
ctypedef IActivityParallel *IActivityParallelP
ctypedef UP[IActivityParallel] IActivityParallelUP
ctypedef IMonitorActivityOverlap *IMonitorActivityOverlapP
ctypedef UP[IMonitorActivityOverlap] IMonitorActivityOverlapUP
ctypedef IMonitorActivitySchedule *IMonitorActivityScheduleP
ctypedef UP[IMonitorActivitySchedule] IMonitorActivityScheduleUP
ctypedef IActivitySchedule *IActivityScheduleP
ctypedef UP[IActivitySchedule] IActivityScheduleUP
ctypedef IMonitorActivitySequence *IMonitorActivitySequenceP
ctypedef UP[IMonitorActivitySequence] IMonitorActivitySequenceUP
ctypedef ITemplateVarDecl *ITemplateVarDeclP
ctypedef UP[ITemplateVarDecl] ITemplateVarDeclUP
ctypedef IActivitySequence *IActivitySequenceP
ctypedef UP[IActivitySequence] IActivitySequenceUP
ctypedef IMonitorActivitySelect *IMonitorActivitySelectP
ctypedef UP[IMonitorActivitySelect] IMonitorActivitySelectUP
ctypedef ITemplateIfClause *ITemplateIfClauseP
ctypedef UP[ITemplateIfClause] ITemplateIfClauseUP
ctypedef ITemplateForeach *ITemplateForeachP
ctypedef UP[ITemplateForeach] ITemplateForeachUP
ctypedef ITemplateRepeat *ITemplateRepeatP
ctypedef UP[ITemplateRepeat] ITemplateRepeatUP
cdef extern from "pssp/ast/AssignOp.h" namespace "pssp::ast":
    cdef enum AssignOp:
        AssignOp_AssignOp_Eq "pssp::ast::AssignOp::AssignOp_Eq"
        AssignOp_AssignOp_PlusEq "pssp::ast::AssignOp::AssignOp_PlusEq"
        AssignOp_AssignOp_MinusEq "pssp::ast::AssignOp::AssignOp_MinusEq"
        AssignOp_AssignOp_ShlEq "pssp::ast::AssignOp::AssignOp_ShlEq"
        AssignOp_AssignOp_ShrEq "pssp::ast::AssignOp::AssignOp_ShrEq"
        AssignOp_AssignOp_OrEq "pssp::ast::AssignOp::AssignOp_OrEq"
        AssignOp_AssignOp_AndEq "pssp::ast::AssignOp::AssignOp_AndEq"
cdef extern from "pssp/ast/CommentPlacement.h" namespace "pssp::ast":
    cdef enum CommentPlacement:
        CommentPlacement_CommentPlacement_Leading "pssp::ast::CommentPlacement::CommentPlacement_Leading"
        CommentPlacement_CommentPlacement_Trailing "pssp::ast::CommentPlacement::CommentPlacement_Trailing"
        CommentPlacement_CommentPlacement_Orphan "pssp::ast::CommentPlacement::CommentPlacement_Orphan"
cdef extern from "pssp/ast/CovergroupBinsKindE.h" namespace "pssp::ast":
    cdef enum CovergroupBinsKindE:
        CovergroupBinsKindE_Bins "pssp::ast::CovergroupBinsKindE::Bins"
        CovergroupBinsKindE_IllegalBins "pssp::ast::CovergroupBinsKindE::IllegalBins"
        CovergroupBinsKindE_IgnoreBins "pssp::ast::CovergroupBinsKindE::IgnoreBins"
cdef extern from "pssp/ast/CoverpointBinsFormE.h" namespace "pssp::ast":
    cdef enum CoverpointBinsFormE:
        CoverpointBinsFormE_Ranges "pssp::ast::CoverpointBinsFormE::Ranges"
        CoverpointBinsFormE_Coverpoint "pssp::ast::CoverpointBinsFormE::Coverpoint"
        CoverpointBinsFormE_Default "pssp::ast::CoverpointBinsFormE::Default"
cdef extern from "pssp/ast/DocCommentForm.h" namespace "pssp::ast":
    cdef enum DocCommentForm:
        DocCommentForm_DocForm_None "pssp::ast::DocCommentForm::DocForm_None"
        DocCommentForm_DocForm_Line "pssp::ast::DocCommentForm::DocForm_Line"
        DocCommentForm_DocForm_DocLine "pssp::ast::DocCommentForm::DocForm_DocLine"
        DocCommentForm_DocForm_Block "pssp::ast::DocCommentForm::DocForm_Block"
        DocCommentForm_DocForm_DocBlock "pssp::ast::DocCommentForm::DocForm_DocBlock"
cdef extern from "pssp/ast/ExecKind.h" namespace "pssp::ast":
    cdef enum ExecKind:
        ExecKind_ExecKind_Body "pssp::ast::ExecKind::ExecKind_Body"
        ExecKind_ExecKind_Header "pssp::ast::ExecKind::ExecKind_Header"
        ExecKind_ExecKind_Declaration "pssp::ast::ExecKind::ExecKind_Declaration"
        ExecKind_ExecKind_RunStart "pssp::ast::ExecKind::ExecKind_RunStart"
        ExecKind_ExecKind_RunEnd "pssp::ast::ExecKind::ExecKind_RunEnd"
        ExecKind_ExecKind_InitDown "pssp::ast::ExecKind::ExecKind_InitDown"
        ExecKind_ExecKind_InitUp "pssp::ast::ExecKind::ExecKind_InitUp"
        ExecKind_ExecKind_PreSolve "pssp::ast::ExecKind::ExecKind_PreSolve"
        ExecKind_ExecKind_PostSolve "pssp::ast::ExecKind::ExecKind_PostSolve"
        ExecKind_ExecKind_PreBody "pssp::ast::ExecKind::ExecKind_PreBody"
        ExecKind_ExecKind_File "pssp::ast::ExecKind::ExecKind_File"
cdef extern from "pssp/ast/ExprBinOp.h" namespace "pssp::ast":
    cdef enum ExprBinOp:
        ExprBinOp_BinOp_LogOr "pssp::ast::ExprBinOp::BinOp_LogOr"
        ExprBinOp_BinOp_LogAnd "pssp::ast::ExprBinOp::BinOp_LogAnd"
        ExprBinOp_BinOp_BitOr "pssp::ast::ExprBinOp::BinOp_BitOr"
        ExprBinOp_BinOp_BitXor "pssp::ast::ExprBinOp::BinOp_BitXor"
        ExprBinOp_BinOp_BitAnd "pssp::ast::ExprBinOp::BinOp_BitAnd"
        ExprBinOp_BinOp_Lt "pssp::ast::ExprBinOp::BinOp_Lt"
        ExprBinOp_BinOp_Le "pssp::ast::ExprBinOp::BinOp_Le"
        ExprBinOp_BinOp_Gt "pssp::ast::ExprBinOp::BinOp_Gt"
        ExprBinOp_BinOp_Ge "pssp::ast::ExprBinOp::BinOp_Ge"
        ExprBinOp_BinOp_Exp "pssp::ast::ExprBinOp::BinOp_Exp"
        ExprBinOp_BinOp_Mul "pssp::ast::ExprBinOp::BinOp_Mul"
        ExprBinOp_BinOp_Div "pssp::ast::ExprBinOp::BinOp_Div"
        ExprBinOp_BinOp_Mod "pssp::ast::ExprBinOp::BinOp_Mod"
        ExprBinOp_BinOp_Add "pssp::ast::ExprBinOp::BinOp_Add"
        ExprBinOp_BinOp_Sub "pssp::ast::ExprBinOp::BinOp_Sub"
        ExprBinOp_BinOp_Shl "pssp::ast::ExprBinOp::BinOp_Shl"
        ExprBinOp_BinOp_Shr "pssp::ast::ExprBinOp::BinOp_Shr"
        ExprBinOp_BinOp_Eq "pssp::ast::ExprBinOp::BinOp_Eq"
        ExprBinOp_BinOp_Ne "pssp::ast::ExprBinOp::BinOp_Ne"
cdef extern from "pssp/ast/ExprUnaryOp.h" namespace "pssp::ast":
    cdef enum ExprUnaryOp:
        ExprUnaryOp_UnaryOp_Plus "pssp::ast::ExprUnaryOp::UnaryOp_Plus"
        ExprUnaryOp_UnaryOp_Minus "pssp::ast::ExprUnaryOp::UnaryOp_Minus"
        ExprUnaryOp_UnaryOp_LogNot "pssp::ast::ExprUnaryOp::UnaryOp_LogNot"
        ExprUnaryOp_UnaryOp_BitNeg "pssp::ast::ExprUnaryOp::UnaryOp_BitNeg"
        ExprUnaryOp_UnaryOp_BitAnd "pssp::ast::ExprUnaryOp::UnaryOp_BitAnd"
        ExprUnaryOp_UnaryOp_BitOr "pssp::ast::ExprUnaryOp::UnaryOp_BitOr"
        ExprUnaryOp_UnaryOp_BitXor "pssp::ast::ExprUnaryOp::UnaryOp_BitXor"
cdef extern from "pssp/ast/ExtendTargetE.h" namespace "pssp::ast":
    cdef enum ExtendTargetE:
        ExtendTargetE_Action "pssp::ast::ExtendTargetE::Action"
        ExtendTargetE_Annotation "pssp::ast::ExtendTargetE::Annotation"
        ExtendTargetE_Buffer "pssp::ast::ExtendTargetE::Buffer"
        ExtendTargetE_Component "pssp::ast::ExtendTargetE::Component"
        ExtendTargetE_Enum "pssp::ast::ExtendTargetE::Enum"
        ExtendTargetE_Resource "pssp::ast::ExtendTargetE::Resource"
        ExtendTargetE_State "pssp::ast::ExtendTargetE::State"
        ExtendTargetE_Stream "pssp::ast::ExtendTargetE::Stream"
        ExtendTargetE_Struct "pssp::ast::ExtendTargetE::Struct"
cdef extern from "pssp/ast/FunctionParamDeclKind.h" namespace "pssp::ast":
    cdef enum FunctionParamDeclKind:
        FunctionParamDeclKind_ParamKind_DataType "pssp::ast::FunctionParamDeclKind::ParamKind_DataType"
        FunctionParamDeclKind_ParamKind_Type "pssp::ast::FunctionParamDeclKind::ParamKind_Type"
        FunctionParamDeclKind_ParamKind_RefAction "pssp::ast::FunctionParamDeclKind::ParamKind_RefAction"
        FunctionParamDeclKind_ParamKind_RefComponent "pssp::ast::FunctionParamDeclKind::ParamKind_RefComponent"
        FunctionParamDeclKind_ParamKind_RefBuffer "pssp::ast::FunctionParamDeclKind::ParamKind_RefBuffer"
        FunctionParamDeclKind_ParamKind_RefResource "pssp::ast::FunctionParamDeclKind::ParamKind_RefResource"
        FunctionParamDeclKind_ParamKind_RefState "pssp::ast::FunctionParamDeclKind::ParamKind_RefState"
        FunctionParamDeclKind_ParamKind_RefStream "pssp::ast::FunctionParamDeclKind::ParamKind_RefStream"
        FunctionParamDeclKind_ParamKind_RefStruct "pssp::ast::FunctionParamDeclKind::ParamKind_RefStruct"
        FunctionParamDeclKind_ParamKind_Struct "pssp::ast::FunctionParamDeclKind::ParamKind_Struct"
        FunctionParamDeclKind_ParamKind_RefMonitor "pssp::ast::FunctionParamDeclKind::ParamKind_RefMonitor"
        FunctionParamDeclKind_ParamKind_Numeric "pssp::ast::FunctionParamDeclKind::ParamKind_Numeric"
cdef extern from "pssp/ast/ParamDir.h" namespace "pssp::ast":
    cdef enum ParamDir:
        ParamDir_ParamDir_Default "pssp::ast::ParamDir::ParamDir_Default"
        ParamDir_ParamDir_In "pssp::ast::ParamDir::ParamDir_In"
        ParamDir_ParamDir_Out "pssp::ast::ParamDir::ParamDir_Out"
        ParamDir_ParamDir_InOut "pssp::ast::ParamDir::ParamDir_InOut"
cdef extern from "pssp/ast/PlatQual.h" namespace "pssp::ast":
    cdef enum PlatQual:
        PlatQual_PlatQual_None "pssp::ast::PlatQual::PlatQual_None"
        PlatQual_PlatQual_Target "pssp::ast::PlatQual::PlatQual_Target"
        PlatQual_PlatQual_Solve "pssp::ast::PlatQual::PlatQual_Solve"
cdef extern from "pssp/ast/StringMethodId.h" namespace "pssp::ast":
    cdef enum StringMethodId:
        StringMethodId_StringMethod_None "pssp::ast::StringMethodId::StringMethod_None"
        StringMethodId_StringMethod_Size "pssp::ast::StringMethodId::StringMethod_Size"
        StringMethodId_StringMethod_Find "pssp::ast::StringMethodId::StringMethod_Find"
        StringMethodId_StringMethod_FindLast "pssp::ast::StringMethodId::StringMethod_FindLast"
        StringMethodId_StringMethod_FindAll "pssp::ast::StringMethodId::StringMethod_FindAll"
        StringMethodId_StringMethod_Lower "pssp::ast::StringMethodId::StringMethod_Lower"
        StringMethodId_StringMethod_Upper "pssp::ast::StringMethodId::StringMethod_Upper"
        StringMethodId_StringMethod_Split "pssp::ast::StringMethodId::StringMethod_Split"
        StringMethodId_StringMethod_Chars "pssp::ast::StringMethodId::StringMethod_Chars"
cdef extern from "pssp/ast/StructKind.h" namespace "pssp::ast":
    cdef enum StructKind:
        StructKind_Buffer "pssp::ast::StructKind::Buffer"
        StructKind_Struct "pssp::ast::StructKind::Struct"
        StructKind_Resource "pssp::ast::StructKind::Resource"
        StructKind_Stream "pssp::ast::StructKind::Stream"
        StructKind_State "pssp::ast::StructKind::State"
cdef extern from "pssp/ast/SymbolRefPathElemKind.h" namespace "pssp::ast":
    cdef enum SymbolRefPathElemKind:
        SymbolRefPathElemKind_ElemKind_ChildIdx "pssp::ast::SymbolRefPathElemKind::ElemKind_ChildIdx"
        SymbolRefPathElemKind_ElemKind_ArgIdx "pssp::ast::SymbolRefPathElemKind::ElemKind_ArgIdx"
        SymbolRefPathElemKind_ElemKind_Inline "pssp::ast::SymbolRefPathElemKind::ElemKind_Inline"
        SymbolRefPathElemKind_ElemKind_ParamIdx "pssp::ast::SymbolRefPathElemKind::ElemKind_ParamIdx"
        SymbolRefPathElemKind_ElemKind_Super "pssp::ast::SymbolRefPathElemKind::ElemKind_Super"
        SymbolRefPathElemKind_ElemKind_TypeSpec "pssp::ast::SymbolRefPathElemKind::ElemKind_TypeSpec"
        SymbolRefPathElemKind_ElemKind_TemplateScope "pssp::ast::SymbolRefPathElemKind::ElemKind_TemplateScope"
cdef extern from "pssp/ast/TypeCategory.h" namespace "pssp::ast":
    cdef enum TypeCategory:
        TypeCategory_Action "pssp::ast::TypeCategory::Action"
        TypeCategory_Component "pssp::ast::TypeCategory::Component"
        TypeCategory_Buffer "pssp::ast::TypeCategory::Buffer"
        TypeCategory_Resource "pssp::ast::TypeCategory::Resource"
        TypeCategory_State "pssp::ast::TypeCategory::State"
        TypeCategory_Stream "pssp::ast::TypeCategory::Stream"
        TypeCategory_Struct "pssp::ast::TypeCategory::Struct"
        TypeCategory_Monitor "pssp::ast::TypeCategory::Monitor"
        TypeCategory_Numeric "pssp::ast::TypeCategory::Numeric"
cdef extern from "pssp/ast/Location.h" namespace "pssp::ast":
    cdef cppclass Location:
        int32_t fileid
        int32_t lineno
        int32_t linepos
        int32_t extent
cdef extern from "pssp/ast/SymbolRefPathElem.h" namespace "pssp::ast":
    cdef cppclass SymbolRefPathElem:
        SymbolRefPathElemKind kind
        int32_t idx
cdef extern from "pssp/ast/FieldAttr.h" namespace "pssp::ast":
    cdef enum FieldAttr:
        FieldAttr_Action "pssp::ast::FieldAttr::Action"
        FieldAttr_Builtin "pssp::ast::FieldAttr::Builtin"
        FieldAttr_Rand "pssp::ast::FieldAttr::Rand"
        FieldAttr_Const "pssp::ast::FieldAttr::Const"
        FieldAttr_Static "pssp::ast::FieldAttr::Static"
        FieldAttr_Instance "pssp::ast::FieldAttr::Instance"
        FieldAttr_Private "pssp::ast::FieldAttr::Private"
        FieldAttr_Protected "pssp::ast::FieldAttr::Protected"
        FieldAttr_Mutable "pssp::ast::FieldAttr::Mutable"
ctypedef IFactory *IFactoryP
cdef extern from "pssp/ast/IFactory.h" namespace "pssp::ast":
    cdef cppclass IFactory:
        ISymbolImportSpec *mkSymbolImportSpec(
                )
        IAssocData *mkAssocData(
                )
        ISymbolRefPath *mkSymbolRefPath(
                )
        ITemplateParamDeclList *mkTemplateParamDeclList(
                )
        IActivityMatchChoice *mkActivityMatchChoice(
                bool is_default,
                IExprOpenRangeListP cond,
                IScopeChildP body)
        ITemplateParamValue *mkTemplateParamValue(
                )
        ITemplateParamValueList *mkTemplateParamValueList(
                )
        IExpr *mkExpr(
                )
        IScopeChild *mkScopeChild(
                )
        IActivitySelectBranch *mkActivitySelectBranch(
                IExprP guard,
                IExprP weight,
                IScopeChildP body)
        IExprAggrMapElem *mkExprAggrMapElem(
                IExprP lhs,
                IExprP rhs)
        IExprAggrStructElem *mkExprAggrStructElem(
                IExprIdP name,
                IExprP value)
        IActionFieldInitializer *mkActionFieldInitializer(
                IExprHierarchicalIdP path,
                IExprP value)
        IFunctionDefinition *mkFunctionDefinition(
                IFunctionPrototypeP proto,
                IExecScopeP body,
                PlatQual plat)
        IFunctionImport *mkFunctionImport(
                PlatQual plat,
                std_string lang)
        IFunctionParamDecl *mkFunctionParamDecl(
                FunctionParamDeclKind kind,
                IExprIdP name,
                IDataTypeP type,
                ParamDir dir,
                IExprP dflt)
        ITypedefDeclaration *mkTypedefDeclaration(
                IExprIdP name,
                IDataTypeP type)
        IGenericConstraintDeclValue *mkGenericConstraintDeclValue(
                )
        IActivityJoinSpec *mkActivityJoinSpec(
                )
        IGenericConstraintParam *mkGenericConstraintParam(
                IExprIdP name,
                bool is_const,
                bool is_numeric,
                IDataTypeP type)
        IMethodParameterList *mkMethodParameterList(
                )
        IActivitySchedulingConstraint *mkActivitySchedulingConstraint(
                bool is_parallel)
        IMonitorActivityStmt *mkMonitorActivityStmt(
                )
        IActivityStmt *mkActivityStmt(
                )
        INamedScopeChild *mkNamedScopeChild(
                IExprIdP name)
        IOverrideStmt *mkOverrideStmt(
                )
        IAnnotation *mkAnnotation(
                ITypeIdentifierP type)
        IPackageImportStmt *mkPackageImportStmt(
                bool wildcard,
                IExprIdP alias)
        IAnnotationParam *mkAnnotationParam(
                IExprIdP name,
                IExprP value)
        IComment *mkComment(
                std_string text,
                CommentPlacement placement)
        IComponentBind *mkComponentBind(
                std_string pool_path,
                bool is_wildcard)
        IComponentBindTarget *mkComponentBindTarget(
                bool is_wildcard)
        IComponentPathElem *mkComponentPathElem(
                IExprIdP id)
        IProceduralStmtIfClause *mkProceduralStmtIfClause(
                IExprP cond,
                IScopeChildP body)
        IConstraintStmt *mkConstraintStmt(
                )
        IPyImportFromStmt *mkPyImportFromStmt(
                )
        IPyImportStmt *mkPyImportStmt(
                )
        IScope *mkScope(
                )
        ICoverStmtReference *mkCoverStmtReference(
                ITypeIdentifierP target)
        IScopeChildRef *mkScopeChildRef(
                IScopeChildP target)
        ISymbolChild *mkSymbolChild(
                )
        ICovergroupOption *mkCovergroupOption(
                IExprIdP name,
                IExprP value)
        ICovergroupPortmap *mkCovergroupPortmap(
                IExprIdP name,
                IExprHierarchicalIdP target)
        IDataType *mkDataType(
                )
        ITargetTemplateFunction *mkTargetTemplateFunction(
                IFunctionPrototypeP proto,
                std_string language,
                std_string data)
        IDistItem *mkDistItem(
                IExprOpenRangeValueP range,
                IDistWeightP weight)
        IDistWeight *mkDistWeight(
                bool is_dividing,
                IExprP expr)
        ITemplateParamDecl *mkTemplateParamDecl(
                IExprIdP name)
        IExecBlockTag *mkExecBlockTag(
                ITypeIdentifierP type)
        ITemplateParamExprValue *mkTemplateParamExprValue(
                IExprP value)
        IExecStmt *mkExecStmt(
                )
        IExecTargetTemplateBlock *mkExecTargetTemplateBlock(
                ExecKind kind,
                std_string data)
        IExportAction *mkExportAction(
                PlatQual plat,
                ITypeIdentifierP target)
        IExportFunction *mkExportFunction(
                PlatQual plat,
                IExprIdP name)
        ITemplateParamTypeValue *mkTemplateParamTypeValue(
                IDataTypeP value)
        IExprAggrLiteral *mkExprAggrLiteral(
                )
        ITypeIdentifier *mkTypeIdentifier(
                )
        ITypeIdentifierElem *mkTypeIdentifierElem(
                IExprIdP id,
                ITemplateParamValueListP params)
        IExprBin *mkExprBin(
                IExprP lhs,
                ExprBinOp op,
                IExprP rhs)
        IExprBitSlice *mkExprBitSlice(
                IExprP lhs,
                IExprP rhs)
        IExprBool *mkExprBool(
                bool value)
        IExprCast *mkExprCast(
                IDataTypeP casting_type,
                IExprP expr)
        IExprCompileHas *mkExprCompileHas(
                IExprRefPathStaticP ref)
        IExprCond *mkExprCond(
                IExprP cond_e,
                IExprP true_e,
                IExprP false_e)
        IExprDomainOpenRangeList *mkExprDomainOpenRangeList(
                )
        IExprDomainOpenRangeValue *mkExprDomainOpenRangeValue(
                bool single,
                IExprP lhs,
                IExprP rhs)
        IExprFloatLiteral *mkExprFloatLiteral(
                double value,
                std_string image,
                bool is_scientific)
        IExprHierarchicalId *mkExprHierarchicalId(
                )
        IExprId *mkExprId(
                std_string id,
                bool is_escaped)
        IExprIn *mkExprIn(
                IExprP lhs,
                IExprOpenRangeListP rhs,
                IExprP collection)
        IExprMemberPathElem *mkExprMemberPathElem(
                IExprIdP id,
                IMethodParameterListP params)
        IExprNull *mkExprNull(
                )
        IExprNumber *mkExprNumber(
                )
        IExprOpenRangeList *mkExprOpenRangeList(
                )
        IExprOpenRangeValue *mkExprOpenRangeValue(
                IExprP lhs,
                IExprP rhs)
        IExprRefPath *mkExprRefPath(
                )
        IExprSliceRange *mkExprSliceRange(
                )
        IExprString *mkExprString(
                std_string value,
                bool is_raw)
        IExprUnary *mkExprUnary(
                ExprUnaryOp op,
                IExprP rhs)
        IExtendEnum *mkExtendEnum(
                ITypeIdentifierP target)
        IActionHandleField *mkActionHandleField(
                IExprIdP name,
                IDataTypeP type)
        IActivityBindStmt *mkActivityBindStmt(
                IExprHierarchicalIdP lhs)
        IActivityConstraint *mkActivityConstraint(
                IConstraintStmtP constraint)
        IActivityJoinSpecBranch *mkActivityJoinSpecBranch(
                )
        IActivityJoinSpecFirst *mkActivityJoinSpecFirst(
                IExprP count)
        IActivityJoinSpecNone *mkActivityJoinSpecNone(
                )
        IActivityJoinSpecSelect *mkActivityJoinSpecSelect(
                IExprP count)
        IActivityLabeledStmt *mkActivityLabeledStmt(
                )
        IActivitySymbolCall *mkActivitySymbolCall(
                IExprIdP target)
        IConstraintScope *mkConstraintScope(
                )
        IConstraintStmtDefault *mkConstraintStmtDefault(
                IExprHierarchicalIdP hid,
                IExprP expr)
        IConstraintStmtDefaultDisable *mkConstraintStmtDefaultDisable(
                IExprHierarchicalIdP hid)
        IConstraintStmtDist *mkConstraintStmtDist(
                IExprP lhs)
        IConstraintStmtExpr *mkConstraintStmtExpr(
                IExprP expr)
        IConstraintStmtField *mkConstraintStmtField(
                IExprIdP name,
                IDataTypeP type)
        IConstraintStmtIf *mkConstraintStmtIf(
                IExprP cond,
                IConstraintScopeP true_c,
                IConstraintScopeP false_c)
        IConstraintStmtSoft *mkConstraintStmtSoft(
                IExprP expr)
        IConstraintStmtUnique *mkConstraintStmtUnique(
                )
        ICoverStmtInline *mkCoverStmtInline(
                )
        ICovergroup *mkCovergroup(
                IExprIdP name)
        ICovergroupCoverpoint *mkCovergroupCoverpoint(
                IExprIdP name,
                IExprP target)
        ICovergroupCross *mkCovergroupCross(
                IExprIdP name)
        ICovergroupCrossBins *mkCovergroupCrossBins(
                IExprIdP name,
                CovergroupBinsKindE kind,
                IExprIdP target,
                IExprP with_expr)
        ICovergroupInstantiation *mkCovergroupInstantiation(
                IExprIdP name,
                ITypeIdentifierP type)
        ICoverpointBins *mkCoverpointBins(
                IExprIdP name,
                CovergroupBinsKindE kind,
                CoverpointBinsFormE form)
        IDataTypeBool *mkDataTypeBool(
                )
        IDataTypeChandle *mkDataTypeChandle(
                )
        IDataTypeEnum *mkDataTypeEnum(
                IDataTypeUserDefinedP tid,
                IExprOpenRangeListP in_rangelist)
        IDataTypeFloat *mkDataTypeFloat(
                bool is_float64)
        IDataTypeInt *mkDataTypeInt(
                bool is_signed,
                IExprP width,
                IExprDomainOpenRangeListP in_range)
        IDataTypePyObj *mkDataTypePyObj(
                )
        IDataTypeRef *mkDataTypeRef(
                IDataTypeUserDefinedP type)
        IDataTypeString *mkDataTypeString(
                bool has_range)
        IDataTypeUserDefined *mkDataTypeUserDefined(
                bool is_global,
                ITypeIdentifierP type_id)
        IEnumDecl *mkEnumDecl(
                IExprIdP name)
        IEnumItem *mkEnumItem(
                IExprIdP name,
                IExprP value)
        IExprAggrEmpty *mkExprAggrEmpty(
                )
        IExprAggrList *mkExprAggrList(
                )
        IExprAggrMap *mkExprAggrMap(
                )
        IExprAggrStruct *mkExprAggrStruct(
                )
        IExprRefPathContext *mkExprRefPathContext(
                IExprHierarchicalIdP hier_id)
        IExprRefPathStatic *mkExprRefPathStatic(
                bool is_global)
        IExprRefPathStaticRooted *mkExprRefPathStaticRooted(
                IExprRefPathStaticP root,
                IExprHierarchicalIdP leaf)
        IExprSignedNumber *mkExprSignedNumber(
                std_string image,
                int32_t width,
                int64_t value)
        IExprTemplateString *mkExprTemplateString(
                std_string value,
                bool is_raw)
        IExprUnsignedNumber *mkExprUnsignedNumber(
                std_string image,
                int32_t width,
                uint64_t value)
        IExtendType *mkExtendType(
                ExtendTargetE kind,
                ITypeIdentifierP target)
        IField *mkField(
                IExprIdP name,
                IDataTypeP type,
                FieldAttr attr,
                IExprP init)
        IFieldClaim *mkFieldClaim(
                IExprIdP name,
                IDataTypeUserDefinedP type,
                bool is_lock)
        IFieldCompRef *mkFieldCompRef(
                IExprIdP name,
                IDataTypeUserDefinedP type)
        IFieldPool *mkFieldPool(
                IExprIdP name,
                IDataTypeUserDefinedP type,
                IExprP size)
        IFieldRef *mkFieldRef(
                IExprIdP name,
                IDataTypeUserDefinedP type,
                bool is_input)
        IFunctionImportProto *mkFunctionImportProto(
                PlatQual plat,
                std_string lang,
                IFunctionPrototypeP proto)
        IFunctionImportType *mkFunctionImportType(
                PlatQual plat,
                std_string lang,
                ITypeIdentifierP type)
        IFunctionPrototype *mkFunctionPrototype(
                IExprIdP name,
                IDataTypeP rtype,
                bool is_target,
                bool is_solve)
        IGlobalScope *mkGlobalScope(
                int32_t fileid)
        IInstanceOverride *mkInstanceOverride(
                IExprHierarchicalIdP target,
                ITypeIdentifierP with_t)
        IMonitorActivityLabeledStmt *mkMonitorActivityLabeledStmt(
                )
        IMonitorConstraint *mkMonitorConstraint(
                IConstraintStmtP constraint)
        INamedScope *mkNamedScope(
                IExprIdP name)
        IOverrideDecl *mkOverrideDecl(
                )
        IPackageScope *mkPackageScope(
                )
        IProceduralStmtAssignment *mkProceduralStmtAssignment(
                IExprP lhs,
                AssignOp op,
                IExprP rhs)
        IProceduralStmtBody *mkProceduralStmtBody(
                IScopeChildP body)
        IProceduralStmtBreak *mkProceduralStmtBreak(
                )
        IProceduralStmtContinue *mkProceduralStmtContinue(
                )
        IProceduralStmtDataDeclaration *mkProceduralStmtDataDeclaration(
                IExprIdP name,
                IDataTypeP datatype,
                IExprP init)
        IProceduralStmtExpr *mkProceduralStmtExpr(
                IExprP expr)
        IProceduralStmtIfElse *mkProceduralStmtIfElse(
                )
        IProceduralStmtMatch *mkProceduralStmtMatch(
                IExprP expr)
        IProceduralStmtMatchChoice *mkProceduralStmtMatchChoice(
                bool is_default,
                IExprOpenRangeListP cond,
                IScopeChildP body)
        IProceduralStmtRandomize *mkProceduralStmtRandomize(
                IExprP target)
        IProceduralStmtReturn *mkProceduralStmtReturn(
                IExprP expr)
        IProceduralStmtSuper *mkProceduralStmtSuper(
                )
        IProceduralStmtYield *mkProceduralStmtYield(
                )
        ISymbolChildrenScope *mkSymbolChildrenScope(
                std_string name)
        ITemplateCategoryTypeParamDecl *mkTemplateCategoryTypeParamDecl(
                IExprIdP name,
                TypeCategory category,
                ITypeIdentifierP restriction,
                IDataTypeP dflt)
        ITemplateGenericTypeParamDecl *mkTemplateGenericTypeParamDecl(
                IExprIdP name,
                IDataTypeP dflt)
        ITemplateValueParamDecl *mkTemplateValueParamDecl(
                IExprIdP name,
                IDataTypeP type,
                IExprP dflt)
        ITypeOverride *mkTypeOverride(
                ITypeIdentifierP target,
                ITypeIdentifierP with_t)
        IActivityActionHandleTraversal *mkActivityActionHandleTraversal(
                IExprRefPathContextP target,
                IConstraintStmtP with_c)
        IActivityActionTypeTraversal *mkActivityActionTypeTraversal(
                IDataTypeUserDefinedP target,
                IConstraintStmtP with_c)
        IActivityAtomicBlock *mkActivityAtomicBlock(
                IScopeChildP body)
        IActivityForeach *mkActivityForeach(
                IExprIdP it_id,
                IExprIdP idx_id,
                IExprRefPathContextP target,
                IScopeChildP body)
        IActivityIfElse *mkActivityIfElse(
                IExprP cond,
                IScopeChildP true_s,
                IScopeChildP false_s)
        IActivityMatch *mkActivityMatch(
                IExprP cond)
        IMonitorActivityEventually *mkMonitorActivityEventually(
                IScopeChildP body)
        IActivityRepeatCount *mkActivityRepeatCount(
                IExprIdP loop_var,
                IExprP count,
                IScopeChildP body)
        IActivityRepeatWhile *mkActivityRepeatWhile(
                IExprP cond,
                IScopeChildP body)
        IActivityReplicate *mkActivityReplicate(
                IExprIdP idx_id,
                IExprP count,
                IExprIdP it_label,
                IScopeChildP body)
        IActivitySelect *mkActivitySelect(
                )
        IActivitySuper *mkActivitySuper(
                )
        IConstraintBlock *mkConstraintBlock(
                std_string name,
                bool is_dynamic)
        IProceduralStmtRepeatWhile *mkProceduralStmtRepeatWhile(
                IScopeChildP body,
                IExprP expr)
        IConstraintStmtForall *mkConstraintStmtForall(
                IExprIdP iterator_id,
                IDataTypeUserDefinedP type_id,
                IExprRefPathP ref_path)
        IConstraintStmtForeach *mkConstraintStmtForeach(
                IExprP expr)
        IProceduralStmtWhile *mkProceduralStmtWhile(
                IScopeChildP body,
                IExprP expr)
        IConstraintStmtImplication *mkConstraintStmtImplication(
                IExprP cond)
        ISymbolScope *mkSymbolScope(
                std_string name)
        ITypeScope *mkTypeScope(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IExprRefPathSuper *mkExprRefPathSuper(
                IExprHierarchicalIdP hier_id)
        IAction *mkAction(
                IExprIdP name,
                ITypeIdentifierP super_t,
                bool is_abstract)
        IActivityDecl *mkActivityDecl(
                std_string name)
        IGenericConstraintDeclBool *mkGenericConstraintDeclBool(
                std_string name,
                bool is_dynamic)
        IImportClass *mkImportClass(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IActivityLabeledScope *mkActivityLabeledScope(
                std_string name)
        IMonitor *mkMonitor(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IMonitorActivityDecl *mkMonitorActivityDecl(
                std_string name)
        IMonitorActivityLabeledScope *mkMonitorActivityLabeledScope(
                std_string name)
        IAnnotationDecl *mkAnnotationDecl(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IComponent *mkComponent(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IProceduralStmtSymbolBodyScope *mkProceduralStmtSymbolBodyScope(
                std_string name,
                IScopeChildP body)
        IConstraintSymbolScope *mkConstraintSymbolScope(
                std_string name)
        IRootSymbolScope *mkRootSymbolScope(
                std_string name)
        IStruct *mkStruct(
                IExprIdP name,
                ITypeIdentifierP super_t,
                StructKind kind)
        ISymbolDeclaration *mkSymbolDeclaration(
                std_string name)
        ISymbolEnumScope *mkSymbolEnumScope(
                std_string name)
        ISymbolExtendScope *mkSymbolExtendScope(
                std_string name)
        ICovergroupType *mkCovergroupType(
                IExprIdP name,
                ITypeIdentifierP super_t)
        ISymbolFunctionScope *mkSymbolFunctionScope(
                std_string name)
        ISymbolTypeScope *mkSymbolTypeScope(
                std_string name,
                ISymbolScopeP plist)
        ITemplateElem *mkTemplateElem(
                std_string name,
                int32_t offset,
                int32_t extent)
        IExecScope *mkExecScope(
                std_string name)
        ITemplateString *mkTemplateString(
                std_string name,
                std_string raw)
        ITemplateText *mkTemplateText(
                std_string name,
                int32_t offset,
                int32_t extent,
                std_string text)
        ITemplateAssign *mkTemplateAssign(
                std_string name,
                int32_t offset,
                int32_t extent,
                IExprIdP lhs,
                IExprP rhs)
        IProceduralStmtForeach *mkProceduralStmtForeach(
                std_string name,
                IScopeChildP body,
                IExprRefPathP path,
                IExprIdP it_id,
                IExprIdP idx_id)
        ITemplateBlock *mkTemplateBlock(
                std_string name,
                int32_t offset,
                int32_t extent)
        ITemplateComment *mkTemplateComment(
                std_string name,
                int32_t offset,
                int32_t extent,
                std_string text)
        ITemplateExpr *mkTemplateExpr(
                std_string name,
                int32_t offset,
                int32_t extent,
                IExprP expr)
        IProceduralStmtRepeat *mkProceduralStmtRepeat(
                std_string name,
                IScopeChildP body,
                IExprIdP it_id,
                IExprP count)
        ITemplateIf *mkTemplateIf(
                std_string name,
                int32_t offset,
                int32_t extent)
        IExecBlock *mkExecBlock(
                std_string name,
                ExecKind kind)
        IMonitorActivityConcat *mkMonitorActivityConcat(
                std_string name)
        IActivityParallel *mkActivityParallel(
                std_string name,
                IActivityJoinSpecP join_spec)
        IMonitorActivityOverlap *mkMonitorActivityOverlap(
                std_string name)
        IMonitorActivitySchedule *mkMonitorActivitySchedule(
                std_string name)
        IActivitySchedule *mkActivitySchedule(
                std_string name,
                IActivityJoinSpecP join_spec)
        IMonitorActivitySequence *mkMonitorActivitySequence(
                std_string name)
        ITemplateVarDecl *mkTemplateVarDecl(
                std_string name,
                int32_t offset,
                int32_t extent)
        IActivitySequence *mkActivitySequence(
                std_string name)
        IMonitorActivitySelect *mkMonitorActivitySelect(
                std_string name)
        ITemplateIfClause *mkTemplateIfClause(
                std_string name,
                int32_t offset,
                int32_t extent)
        ITemplateForeach *mkTemplateForeach(
                std_string name,
                int32_t offset,
                int32_t extent,
                IExprP expr)
        ITemplateRepeat *mkTemplateRepeat(
                std_string name,
                int32_t offset,
                int32_t extent,
                IExprP expr)
cdef extern from "pssp/ast/ISymbolImportSpec.h" namespace "pssp::ast":
    cpdef cppclass ISymbolImportSpec:
        std_vector[IPackageImportStmtP] & getImports();
        std_unordered_map[std_string,UP[ISymbolRefPath]] &getSymtab()
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IAssocData.h" namespace "pssp::ast":
    cpdef cppclass IAssocData:
        pass
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/ISymbolRefPath.h" namespace "pssp::ast":
    cpdef cppclass ISymbolRefPath:
        std_vector[SymbolRefPathElem] & getPath();
        int32_t getPyref_idx()
        
        void setPyref_idx(int32_t v)
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/ITemplateParamDeclList.h" namespace "pssp::ast":
    cpdef cppclass ITemplateParamDeclList:
        std_vector[UP[ITemplateParamDecl]] & getParams();
        bool getSpecialized()
        
        void setSpecialized(bool v)
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IActivityMatchChoice.h" namespace "pssp::ast":
    cpdef cppclass IActivityMatchChoice:
        bool getIs_default()
        
        void setIs_default(bool v)
        IExprOpenRangeList *getCond()
        
        void setCond(IExprOpenRangeList *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/ITemplateParamValue.h" namespace "pssp::ast":
    cpdef cppclass ITemplateParamValue:
        pass
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/ITemplateParamValueList.h" namespace "pssp::ast":
    cpdef cppclass ITemplateParamValueList:
        std_vector[UP[ITemplateParamValue]] & getValues();
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IExpr.h" namespace "pssp::ast":
    cpdef cppclass IExpr:
        pass
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IScopeChild.h" namespace "pssp::ast":
    cpdef cppclass IScopeChild:
        const std_string &getDocstring()
        
        void setDocstring(const std_string & v)
        const std_string &getDocRaw()
        
        void setDocRaw(const std_string & v)
        DocCommentForm getDocForm()
        
        void setDocForm(DocCommentForm v)
        const Location & getDocLocation()
        
        void setDocLocation(const Location &)
        const Location & getLocation()
        
        void setLocation(const Location &)
        const Location & getEndLocation()
        
        void setEndLocation(const Location &)
        IScopeP getParent();
        
        void setParent(IScopeP v)
        int32_t getIndex()
        
        void setIndex(int32_t v)
        IAssocData *getAssocData()
        
        void setAssocData(IAssocData *v)
        std_vector[UP[IAnnotation]] & getAnnotations();
        std_vector[UP[IComment]] & getComments();
        std_vector[UP[IComment]] & getTrailing_comments();
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IActivitySelectBranch.h" namespace "pssp::ast":
    cpdef cppclass IActivitySelectBranch:
        IExpr *getGuard()
        
        void setGuard(IExpr *v)
        IExpr *getWeight()
        
        void setWeight(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IExprAggrMapElem.h" namespace "pssp::ast":
    cpdef cppclass IExprAggrMapElem:
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IExprAggrStructElem.h" namespace "pssp::ast":
    cpdef cppclass IExprAggrStructElem:
        IExprId *getName()
        
        void setName(IExprId *v)
        int32_t getTarget()
        
        void setTarget(int32_t v)
        IExpr *getValue()
        
        void setValue(IExpr *v)
        void accept(VisitorBase *v)

cdef extern from "pssp/ast/IActionFieldInitializer.h" namespace "pssp::ast":
    cpdef cppclass IActionFieldInitializer(IScopeChild):
        IExprHierarchicalId *getPath()
        
        void setPath(IExprHierarchicalId *v)
        IExpr *getValue()
        
        void setValue(IExpr *v)

cdef extern from "pssp/ast/IFunctionDefinition.h" namespace "pssp::ast":
    cpdef cppclass IFunctionDefinition(IScopeChild):
        IFunctionPrototype *getProto()
        
        void setProto(IFunctionPrototype *v)
        IExecScope *getBody()
        
        void setBody(IExecScope *v)
        PlatQual getPlat()
        
        void setPlat(PlatQual v)

cdef extern from "pssp/ast/IFunctionImport.h" namespace "pssp::ast":
    cpdef cppclass IFunctionImport(IScopeChild):
        PlatQual getPlat()
        
        void setPlat(PlatQual v)
        const std_string &getLang()
        
        void setLang(const std_string & v)

cdef extern from "pssp/ast/IFunctionParamDecl.h" namespace "pssp::ast":
    cpdef cppclass IFunctionParamDecl(IScopeChild):
        FunctionParamDeclKind getKind()
        
        void setKind(FunctionParamDeclKind v)
        IExprId *getName()
        
        void setName(IExprId *v)
        IDataType *getType()
        
        void setType(IDataType *v)
        ParamDir getDir()
        
        void setDir(ParamDir v)
        IExpr *getDflt()
        
        void setDflt(IExpr *v)
        bool getIs_varargs()
        
        void setIs_varargs(bool v)

cdef extern from "pssp/ast/ITypedefDeclaration.h" namespace "pssp::ast":
    cpdef cppclass ITypedefDeclaration(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)
        IDataType *getType()
        
        void setType(IDataType *v)

cdef extern from "pssp/ast/IGenericConstraintDeclValue.h" namespace "pssp::ast":
    cpdef cppclass IGenericConstraintDeclValue(IScopeChild):
        bool getIs_static()
        
        void setIs_static(bool v)
        bool getIs_return_numeric()
        
        void setIs_return_numeric(bool v)
        IDataType *getReturn_type()
        
        void setReturn_type(IDataType *v)
        IExprId *getName()
        
        void setName(IExprId *v)
        std_vector[UP[IGenericConstraintParam]] & getParameters();
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IActivityJoinSpec.h" namespace "pssp::ast":
    cpdef cppclass IActivityJoinSpec(IScopeChild):
        pass

cdef extern from "pssp/ast/IGenericConstraintParam.h" namespace "pssp::ast":
    cpdef cppclass IGenericConstraintParam(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)
        bool getIs_const()
        
        void setIs_const(bool v)
        bool getIs_numeric()
        
        void setIs_numeric(bool v)
        IDataType *getType()
        
        void setType(IDataType *v)

cdef extern from "pssp/ast/IMethodParameterList.h" namespace "pssp::ast":
    cpdef cppclass IMethodParameterList(IExpr):
        std_vector[UP[IExpr]] & getParameters();

cdef extern from "pssp/ast/IActivitySchedulingConstraint.h" namespace "pssp::ast":
    cpdef cppclass IActivitySchedulingConstraint(IScopeChild):
        bool getIs_parallel()
        
        void setIs_parallel(bool v)
        std_vector[UP[IExprHierarchicalId]] & getTargets();

cdef extern from "pssp/ast/IMonitorActivityStmt.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivityStmt(IScopeChild):
        pass

cdef extern from "pssp/ast/IActivityStmt.h" namespace "pssp::ast":
    cpdef cppclass IActivityStmt(IScopeChild):
        pass

cdef extern from "pssp/ast/INamedScopeChild.h" namespace "pssp::ast":
    cpdef cppclass INamedScopeChild(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)

cdef extern from "pssp/ast/IOverrideStmt.h" namespace "pssp::ast":
    cpdef cppclass IOverrideStmt(IScopeChild):
        pass

cdef extern from "pssp/ast/IAnnotation.h" namespace "pssp::ast":
    cpdef cppclass IAnnotation(IScopeChild):
        ITypeIdentifier *getType()
        
        void setType(ITypeIdentifier *v)
        std_vector[UP[IAnnotationParam]] & getParameters();
        bool getIs_standalone()
        
        void setIs_standalone(bool v)

cdef extern from "pssp/ast/IPackageImportStmt.h" namespace "pssp::ast":
    cpdef cppclass IPackageImportStmt(IScopeChild):
        bool getWildcard()
        
        void setWildcard(bool v)
        IExprId *getAlias()
        
        void setAlias(IExprId *v)
        ITypeIdentifier *getPath()
        
        void setPath(ITypeIdentifier *v)

cdef extern from "pssp/ast/IAnnotationParam.h" namespace "pssp::ast":
    cpdef cppclass IAnnotationParam(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)
        IExpr *getValue()
        
        void setValue(IExpr *v)

cdef extern from "pssp/ast/IComment.h" namespace "pssp::ast":
    cpdef cppclass IComment(IScopeChild):
        const std_string &getText()
        
        void setText(const std_string & v)
        CommentPlacement getPlacement()
        
        void setPlacement(CommentPlacement v)
        const std_string &getRaw()
        
        void setRaw(const std_string & v)
        bool getIs_block()
        
        void setIs_block(bool v)

cdef extern from "pssp/ast/IComponentBind.h" namespace "pssp::ast":
    cpdef cppclass IComponentBind(IScopeChild):
        const std_string &getPool_path()
        
        void setPool_path(const std_string & v)
        bool getIs_wildcard()
        
        void setIs_wildcard(bool v)
        std_vector[UP[IComponentBindTarget]] & getTargets();

cdef extern from "pssp/ast/IComponentBindTarget.h" namespace "pssp::ast":
    cpdef cppclass IComponentBindTarget(IScopeChild):
        bool getIs_wildcard()
        
        void setIs_wildcard(bool v)
        std_vector[UP[IComponentPathElem]] & getPath();
        ITypeIdentifier *getType_id()
        
        void setType_id(ITypeIdentifier *v)
        IExprId *getField()
        
        void setField(IExprId *v)
        IExprDomainOpenRangeList *getRange()
        
        void setRange(IExprDomainOpenRangeList *v)

cdef extern from "pssp/ast/IComponentPathElem.h" namespace "pssp::ast":
    cpdef cppclass IComponentPathElem(IScopeChild):
        IExprId *getId()
        
        void setId(IExprId *v)
        IExprDomainOpenRangeList *getRange()
        
        void setRange(IExprDomainOpenRangeList *v)

cdef extern from "pssp/ast/IProceduralStmtIfClause.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtIfClause(IScopeChild):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IConstraintStmt.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmt(IScopeChild):
        pass

cdef extern from "pssp/ast/IPyImportFromStmt.h" namespace "pssp::ast":
    cpdef cppclass IPyImportFromStmt(IScopeChild):
        std_vector[UP[IExprId]] & getPath();
        std_vector[UP[IExprId]] & getTargets();

cdef extern from "pssp/ast/IPyImportStmt.h" namespace "pssp::ast":
    cpdef cppclass IPyImportStmt(IScopeChild):
        std_vector[UP[IExprId]] & getPath();
        IExprId *getAlias()
        
        void setAlias(IExprId *v)

cdef extern from "pssp/ast/IScope.h" namespace "pssp::ast":
    cpdef cppclass IScope(IScopeChild):
        std_vector[UP[IScopeChild]] & getChildren();

cdef extern from "pssp/ast/ICoverStmtReference.h" namespace "pssp::ast":
    cpdef cppclass ICoverStmtReference(IScopeChild):
        ITypeIdentifier *getTarget()
        
        void setTarget(ITypeIdentifier *v)
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "pssp/ast/IScopeChildRef.h" namespace "pssp::ast":
    cpdef cppclass IScopeChildRef(IScopeChild):
        IScopeChildP getTarget();
        
        void setTarget(IScopeChildP v)

cdef extern from "pssp/ast/ISymbolChild.h" namespace "pssp::ast":
    cpdef cppclass ISymbolChild(IScopeChild):
        int32_t getId()
        
        void setId(int32_t v)
        ISymbolScopeP getUpper();
        
        void setUpper(ISymbolScopeP v)

cdef extern from "pssp/ast/ICovergroupOption.h" namespace "pssp::ast":
    cpdef cppclass ICovergroupOption(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)
        IExpr *getValue()
        
        void setValue(IExpr *v)

cdef extern from "pssp/ast/ICovergroupPortmap.h" namespace "pssp::ast":
    cpdef cppclass ICovergroupPortmap(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)
        IExprHierarchicalId *getTarget()
        
        void setTarget(IExprHierarchicalId *v)

cdef extern from "pssp/ast/IDataType.h" namespace "pssp::ast":
    cpdef cppclass IDataType(IScopeChild):
        pass

cdef extern from "pssp/ast/ITargetTemplateFunction.h" namespace "pssp::ast":
    cpdef cppclass ITargetTemplateFunction(IScopeChild):
        IFunctionPrototype *getProto()
        
        void setProto(IFunctionPrototype *v)
        const std_string &getLanguage()
        
        void setLanguage(const std_string & v)
        const std_string &getData()
        
        void setData(const std_string & v)
        bool getIs_static()
        
        void setIs_static(bool v)
        ITemplateString *getTemplate()
        
        void setTemplate(ITemplateString *v)

cdef extern from "pssp/ast/IDistItem.h" namespace "pssp::ast":
    cpdef cppclass IDistItem(IScopeChild):
        IExprOpenRangeValue *getRange()
        
        void setRange(IExprOpenRangeValue *v)
        IDistWeight *getWeight()
        
        void setWeight(IDistWeight *v)

cdef extern from "pssp/ast/IDistWeight.h" namespace "pssp::ast":
    cpdef cppclass IDistWeight(IScopeChild):
        bool getIs_dividing()
        
        void setIs_dividing(bool v)
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/ITemplateParamDecl.h" namespace "pssp::ast":
    cpdef cppclass ITemplateParamDecl(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)

cdef extern from "pssp/ast/IExecBlockTag.h" namespace "pssp::ast":
    cpdef cppclass IExecBlockTag(IScopeChild):
        ITypeIdentifier *getType()
        
        void setType(ITypeIdentifier *v)
        IExprAggrStruct *getLiteral()
        
        void setLiteral(IExprAggrStruct *v)

cdef extern from "pssp/ast/ITemplateParamExprValue.h" namespace "pssp::ast":
    cpdef cppclass ITemplateParamExprValue(ITemplateParamValue):
        IExpr *getValue()
        
        void setValue(IExpr *v)

cdef extern from "pssp/ast/IExecStmt.h" namespace "pssp::ast":
    cpdef cppclass IExecStmt(IScopeChild):
        ISymbolScopeP getUpper();
        
        void setUpper(ISymbolScopeP v)

cdef extern from "pssp/ast/IExecTargetTemplateBlock.h" namespace "pssp::ast":
    cpdef cppclass IExecTargetTemplateBlock(IScopeChild):
        ExecKind getKind()
        
        void setKind(ExecKind v)
        const std_string &getData()
        
        void setData(const std_string & v)
        ITemplateString *getTemplate()
        
        void setTemplate(ITemplateString *v)
        const std_string &getLanguage()
        
        void setLanguage(const std_string & v)
        const std_string &getFilename()
        
        void setFilename(const std_string & v)
        ITemplateString *getFilename_template()
        
        void setFilename_template(ITemplateString *v)
        IExecBlockTag *getTag()
        
        void setTag(IExecBlockTag *v)

cdef extern from "pssp/ast/IExportAction.h" namespace "pssp::ast":
    cpdef cppclass IExportAction(IScopeChild):
        PlatQual getPlat()
        
        void setPlat(PlatQual v)
        ITypeIdentifier *getTarget()
        
        void setTarget(ITypeIdentifier *v)
        std_vector[UP[IFunctionParamDecl]] & getParameters();

cdef extern from "pssp/ast/IExportFunction.h" namespace "pssp::ast":
    cpdef cppclass IExportFunction(IScopeChild):
        PlatQual getPlat()
        
        void setPlat(PlatQual v)
        IExprId *getName()
        
        void setName(IExprId *v)

cdef extern from "pssp/ast/ITemplateParamTypeValue.h" namespace "pssp::ast":
    cpdef cppclass ITemplateParamTypeValue(ITemplateParamValue):
        IDataType *getValue()
        
        void setValue(IDataType *v)

cdef extern from "pssp/ast/IExprAggrLiteral.h" namespace "pssp::ast":
    cpdef cppclass IExprAggrLiteral(IExpr):
        pass

cdef extern from "pssp/ast/ITypeIdentifier.h" namespace "pssp::ast":
    cpdef cppclass ITypeIdentifier(IExpr):
        std_vector[UP[ITypeIdentifierElem]] & getElems();
        ISymbolRefPath *getTarget()
        
        void setTarget(ISymbolRefPath *v)

cdef extern from "pssp/ast/ITypeIdentifierElem.h" namespace "pssp::ast":
    cpdef cppclass ITypeIdentifierElem(IExpr):
        IExprId *getId()
        
        void setId(IExprId *v)
        ITemplateParamValueList *getParams()
        
        void setParams(ITemplateParamValueList *v)

cdef extern from "pssp/ast/IExprBin.h" namespace "pssp::ast":
    cpdef cppclass IExprBin(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        ExprBinOp getOp()
        
        void setOp(ExprBinOp v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "pssp/ast/IExprBitSlice.h" namespace "pssp::ast":
    cpdef cppclass IExprBitSlice(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "pssp/ast/IExprBool.h" namespace "pssp::ast":
    cpdef cppclass IExprBool(IExpr):
        bool getValue()
        
        void setValue(bool v)

cdef extern from "pssp/ast/IExprCast.h" namespace "pssp::ast":
    cpdef cppclass IExprCast(IExpr):
        IDataType *getCasting_type()
        
        void setCasting_type(IDataType *v)
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IExprCompileHas.h" namespace "pssp::ast":
    cpdef cppclass IExprCompileHas(IExpr):
        IExprRefPathStatic *getRef()
        
        void setRef(IExprRefPathStatic *v)

cdef extern from "pssp/ast/IExprCond.h" namespace "pssp::ast":
    cpdef cppclass IExprCond(IExpr):
        IExpr *getCond_e()
        
        void setCond_e(IExpr *v)
        IExpr *getTrue_e()
        
        void setTrue_e(IExpr *v)
        IExpr *getFalse_e()
        
        void setFalse_e(IExpr *v)

cdef extern from "pssp/ast/IExprDomainOpenRangeList.h" namespace "pssp::ast":
    cpdef cppclass IExprDomainOpenRangeList(IExpr):
        std_vector[UP[IExprDomainOpenRangeValue]] & getValues();

cdef extern from "pssp/ast/IExprDomainOpenRangeValue.h" namespace "pssp::ast":
    cpdef cppclass IExprDomainOpenRangeValue(IExpr):
        bool getSingle()
        
        void setSingle(bool v)
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "pssp/ast/IExprFloatLiteral.h" namespace "pssp::ast":
    cpdef cppclass IExprFloatLiteral(IExpr):
        double getValue()
        
        void setValue(double v)
        const std_string &getImage()
        
        void setImage(const std_string & v)
        bool getIs_scientific()
        
        void setIs_scientific(bool v)

cdef extern from "pssp/ast/IExprHierarchicalId.h" namespace "pssp::ast":
    cpdef cppclass IExprHierarchicalId(IExpr):
        std_vector[UP[IExprMemberPathElem]] & getElems();

cdef extern from "pssp/ast/IExprId.h" namespace "pssp::ast":
    cpdef cppclass IExprId(IExpr):
        const std_string &getId()
        
        void setId(const std_string & v)
        bool getIs_escaped()
        
        void setIs_escaped(bool v)
        const Location & getLocation()
        
        void setLocation(const Location &)

cdef extern from "pssp/ast/IExprIn.h" namespace "pssp::ast":
    cpdef cppclass IExprIn(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExprOpenRangeList *getRhs()
        
        void setRhs(IExprOpenRangeList *v)
        IExpr *getCollection()
        
        void setCollection(IExpr *v)

cdef extern from "pssp/ast/IExprMemberPathElem.h" namespace "pssp::ast":
    cpdef cppclass IExprMemberPathElem(IExpr):
        IExprId *getId()
        
        void setId(IExprId *v)
        IMethodParameterList *getParams()
        
        void setParams(IMethodParameterList *v)
        std_vector[UP[IExpr]] & getSubscript();
        int32_t getTarget()
        
        void setTarget(int32_t v)
        int32_t getSuper()
        
        void setSuper(int32_t v)
        StringMethodId getString_method_id()
        
        void setString_method_id(StringMethodId v)

cdef extern from "pssp/ast/IExprNull.h" namespace "pssp::ast":
    cpdef cppclass IExprNull(IExpr):
        pass

cdef extern from "pssp/ast/IExprNumber.h" namespace "pssp::ast":
    cpdef cppclass IExprNumber(IExpr):
        pass

cdef extern from "pssp/ast/IExprOpenRangeList.h" namespace "pssp::ast":
    cpdef cppclass IExprOpenRangeList(IExpr):
        std_vector[UP[IExprOpenRangeValue]] & getValues();

cdef extern from "pssp/ast/IExprOpenRangeValue.h" namespace "pssp::ast":
    cpdef cppclass IExprOpenRangeValue(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "pssp/ast/IExprRefPath.h" namespace "pssp::ast":
    cpdef cppclass IExprRefPath(IExpr):
        ISymbolRefPath *getTarget()
        
        void setTarget(ISymbolRefPath *v)

cdef extern from "pssp/ast/IExprSliceRange.h" namespace "pssp::ast":
    cpdef cppclass IExprSliceRange(IExpr):
        IExpr *getLower()
        
        void setLower(IExpr *v)
        IExpr *getUpper()
        
        void setUpper(IExpr *v)

cdef extern from "pssp/ast/IExprString.h" namespace "pssp::ast":
    cpdef cppclass IExprString(IExpr):
        const std_string &getValue()
        
        void setValue(const std_string & v)
        bool getIs_raw()
        
        void setIs_raw(bool v)

cdef extern from "pssp/ast/IExprUnary.h" namespace "pssp::ast":
    cpdef cppclass IExprUnary(IExpr):
        ExprUnaryOp getOp()
        
        void setOp(ExprUnaryOp v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "pssp/ast/IExtendEnum.h" namespace "pssp::ast":
    cpdef cppclass IExtendEnum(IScopeChild):
        ITypeIdentifier *getTarget()
        
        void setTarget(ITypeIdentifier *v)
        std_vector[UP[IEnumItem]] & getItems();

cdef extern from "pssp/ast/IActionHandleField.h" namespace "pssp::ast":
    cpdef cppclass IActionHandleField(INamedScopeChild):
        IDataType *getType()
        
        void setType(IDataType *v)
        std_vector[UP[IActionFieldInitializer]] & getInitializers();

cdef extern from "pssp/ast/IActivityBindStmt.h" namespace "pssp::ast":
    cpdef cppclass IActivityBindStmt(IActivityStmt):
        IExprHierarchicalId *getLhs()
        
        void setLhs(IExprHierarchicalId *v)
        std_vector[UP[IExprHierarchicalId]] & getRhs();

cdef extern from "pssp/ast/IActivityConstraint.h" namespace "pssp::ast":
    cpdef cppclass IActivityConstraint(IActivityStmt):
        IConstraintStmt *getConstraint()
        
        void setConstraint(IConstraintStmt *v)

cdef extern from "pssp/ast/IActivityJoinSpecBranch.h" namespace "pssp::ast":
    cpdef cppclass IActivityJoinSpecBranch(IActivityJoinSpec):
        std_vector[UP[IExprRefPathContext]] & getBranches();

cdef extern from "pssp/ast/IActivityJoinSpecFirst.h" namespace "pssp::ast":
    cpdef cppclass IActivityJoinSpecFirst(IActivityJoinSpec):
        IExpr *getCount()
        
        void setCount(IExpr *v)

cdef extern from "pssp/ast/IActivityJoinSpecNone.h" namespace "pssp::ast":
    cpdef cppclass IActivityJoinSpecNone(IActivityJoinSpec):
        pass

cdef extern from "pssp/ast/IActivityJoinSpecSelect.h" namespace "pssp::ast":
    cpdef cppclass IActivityJoinSpecSelect(IActivityJoinSpec):
        IExpr *getCount()
        
        void setCount(IExpr *v)

cdef extern from "pssp/ast/IActivityLabeledStmt.h" namespace "pssp::ast":
    cpdef cppclass IActivityLabeledStmt(IActivityStmt):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "pssp/ast/IActivitySymbolCall.h" namespace "pssp::ast":
    cpdef cppclass IActivitySymbolCall(IActivityStmt):
        IExprId *getTarget()
        
        void setTarget(IExprId *v)
        std_vector[UP[IExpr]] & getParams();

cdef extern from "pssp/ast/IConstraintScope.h" namespace "pssp::ast":
    cpdef cppclass IConstraintScope(IConstraintStmt):
        std_vector[UP[IConstraintStmt]] & getConstraints();

cdef extern from "pssp/ast/IConstraintStmtDefault.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtDefault(IConstraintStmt):
        IExprHierarchicalId *getHid()
        
        void setHid(IExprHierarchicalId *v)
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IConstraintStmtDefaultDisable.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtDefaultDisable(IConstraintStmt):
        IExprHierarchicalId *getHid()
        
        void setHid(IExprHierarchicalId *v)

cdef extern from "pssp/ast/IConstraintStmtDist.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtDist(IConstraintStmt):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        std_vector[UP[IDistItem]] & getItems();

cdef extern from "pssp/ast/IConstraintStmtExpr.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtExpr(IConstraintStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IConstraintStmtField.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtField(IConstraintStmt):
        IExprId *getName()
        
        void setName(IExprId *v)
        IDataType *getType()
        
        void setType(IDataType *v)

cdef extern from "pssp/ast/IConstraintStmtIf.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtIf(IConstraintStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IConstraintScope *getTrue_c()
        
        void setTrue_c(IConstraintScope *v)
        IConstraintScope *getFalse_c()
        
        void setFalse_c(IConstraintScope *v)

cdef extern from "pssp/ast/IConstraintStmtSoft.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtSoft(IConstraintStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IConstraintStmtUnique.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtUnique(IConstraintStmt):
        std_vector[UP[IExprHierarchicalId]] & getList();
        bool getIs_braced()
        
        void setIs_braced(bool v)

cdef extern from "pssp/ast/ICoverStmtInline.h" namespace "pssp::ast":
    cpdef cppclass ICoverStmtInline(IScope):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "pssp/ast/ICovergroup.h" namespace "pssp::ast":
    cpdef cppclass ICovergroup(INamedScopeChild):
        std_vector[UP[ICovergroupCoverpoint]] & getCoverpoints();
        std_vector[UP[ICovergroupCross]] & getCrosses();
        std_vector[UP[ICovergroupOption]] & getOptions();

cdef extern from "pssp/ast/ICovergroupCoverpoint.h" namespace "pssp::ast":
    cpdef cppclass ICovergroupCoverpoint(INamedScopeChild):
        IExpr *getTarget()
        
        void setTarget(IExpr *v)
        IDataType *getData_type()
        
        void setData_type(IDataType *v)
        IExpr *getIff()
        
        void setIff(IExpr *v)
        std_vector[UP[ICoverpointBins]] & getBins();
        std_vector[UP[ICovergroupOption]] & getOptions();

cdef extern from "pssp/ast/ICovergroupCross.h" namespace "pssp::ast":
    cpdef cppclass ICovergroupCross(INamedScopeChild):
        std_vector[UP[IExprId]] & getCoverpoint_names();
        IExpr *getIff()
        
        void setIff(IExpr *v)
        std_vector[UP[ICovergroupCrossBins]] & getBins();
        std_vector[UP[ICovergroupOption]] & getOptions();

cdef extern from "pssp/ast/ICovergroupCrossBins.h" namespace "pssp::ast":
    cpdef cppclass ICovergroupCrossBins(INamedScopeChild):
        CovergroupBinsKindE getKind()
        
        void setKind(CovergroupBinsKindE v)
        IExprId *getTarget()
        
        void setTarget(IExprId *v)
        IExpr *getWith_expr()
        
        void setWith_expr(IExpr *v)

cdef extern from "pssp/ast/ICovergroupInstantiation.h" namespace "pssp::ast":
    cpdef cppclass ICovergroupInstantiation(INamedScopeChild):
        ITypeIdentifier *getType()
        
        void setType(ITypeIdentifier *v)
        std_vector[UP[ICovergroupPortmap]] & getPortmap();
        std_vector[UP[IExprHierarchicalId]] & getTargets();
        std_vector[UP[ICovergroupOption]] & getOptions();

cdef extern from "pssp/ast/ICoverpointBins.h" namespace "pssp::ast":
    cpdef cppclass ICoverpointBins(INamedScopeChild):
        CovergroupBinsKindE getKind()
        
        void setKind(CovergroupBinsKindE v)
        CoverpointBinsFormE getForm()
        
        void setForm(CoverpointBinsFormE v)
        bool getIs_array()
        
        void setIs_array(bool v)
        IExpr *getArray_size()
        
        void setArray_size(IExpr *v)
        std_vector[UP[IExprOpenRangeValue]] & getRanges();
        IExprId *getTarget()
        
        void setTarget(IExprId *v)
        IExpr *getWith_expr()
        
        void setWith_expr(IExpr *v)

cdef extern from "pssp/ast/IDataTypeBool.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeBool(IDataType):
        pass

cdef extern from "pssp/ast/IDataTypeChandle.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeChandle(IDataType):
        pass

cdef extern from "pssp/ast/IDataTypeEnum.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeEnum(IDataType):
        IDataTypeUserDefined *getTid()
        
        void setTid(IDataTypeUserDefined *v)
        IExprOpenRangeList *getIn_rangelist()
        
        void setIn_rangelist(IExprOpenRangeList *v)

cdef extern from "pssp/ast/IDataTypeFloat.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeFloat(IDataType):
        bool getIs_float64()
        
        void setIs_float64(bool v)

cdef extern from "pssp/ast/IDataTypeInt.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeInt(IDataType):
        bool getIs_signed()
        
        void setIs_signed(bool v)
        IExpr *getWidth()
        
        void setWidth(IExpr *v)
        IExprDomainOpenRangeList *getIn_range()
        
        void setIn_range(IExprDomainOpenRangeList *v)

cdef extern from "pssp/ast/IDataTypePyObj.h" namespace "pssp::ast":
    cpdef cppclass IDataTypePyObj(IDataType):
        pass

cdef extern from "pssp/ast/IDataTypeRef.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeRef(IDataType):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)

cdef extern from "pssp/ast/IDataTypeString.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeString(IDataType):
        bool getHas_range()
        
        void setHas_range(bool v)
        std_vector[std_string] & getIn_range();

cdef extern from "pssp/ast/IDataTypeUserDefined.h" namespace "pssp::ast":
    cpdef cppclass IDataTypeUserDefined(IDataType):
        bool getIs_global()
        
        void setIs_global(bool v)
        ITypeIdentifier *getType_id()
        
        void setType_id(ITypeIdentifier *v)

cdef extern from "pssp/ast/IEnumDecl.h" namespace "pssp::ast":
    cpdef cppclass IEnumDecl(INamedScopeChild):
        std_vector[UP[IEnumItem]] & getItems();
        IDataType *getBase_type()
        
        void setBase_type(IDataType *v)

cdef extern from "pssp/ast/IEnumItem.h" namespace "pssp::ast":
    cpdef cppclass IEnumItem(INamedScopeChild):
        IExpr *getValue()
        
        void setValue(IExpr *v)
        ISymbolEnumScopeP getUpper();
        
        void setUpper(ISymbolEnumScopeP v)

cdef extern from "pssp/ast/IExprAggrEmpty.h" namespace "pssp::ast":
    cpdef cppclass IExprAggrEmpty(IExprAggrLiteral):
        pass

cdef extern from "pssp/ast/IExprAggrList.h" namespace "pssp::ast":
    cpdef cppclass IExprAggrList(IExprAggrLiteral):
        std_vector[UP[IExpr]] & getElems();

cdef extern from "pssp/ast/IExprAggrMap.h" namespace "pssp::ast":
    cpdef cppclass IExprAggrMap(IExprAggrLiteral):
        std_vector[UP[IExprAggrMapElem]] & getElems();

cdef extern from "pssp/ast/IExprAggrStruct.h" namespace "pssp::ast":
    cpdef cppclass IExprAggrStruct(IExprAggrLiteral):
        std_vector[UP[IExprAggrStructElem]] & getElems();

cdef extern from "pssp/ast/IExprRefPathContext.h" namespace "pssp::ast":
    cpdef cppclass IExprRefPathContext(IExprRefPath):
        bool getIs_super()
        
        void setIs_super(bool v)
        IExprHierarchicalId *getHier_id()
        
        void setHier_id(IExprHierarchicalId *v)
        IExprBitSlice *getSlice()
        
        void setSlice(IExprBitSlice *v)

cdef extern from "pssp/ast/IExprRefPathStatic.h" namespace "pssp::ast":
    cpdef cppclass IExprRefPathStatic(IExprRefPath):
        bool getIs_global()
        
        void setIs_global(bool v)
        std_vector[UP[ITypeIdentifierElem]] & getBase();
        IExprBitSlice *getSlice()
        
        void setSlice(IExprBitSlice *v)

cdef extern from "pssp/ast/IExprRefPathStaticRooted.h" namespace "pssp::ast":
    cpdef cppclass IExprRefPathStaticRooted(IExprRefPath):
        IExprRefPathStatic *getRoot()
        
        void setRoot(IExprRefPathStatic *v)
        IExprHierarchicalId *getLeaf()
        
        void setLeaf(IExprHierarchicalId *v)
        IExprBitSlice *getSlice()
        
        void setSlice(IExprBitSlice *v)

cdef extern from "pssp/ast/IExprSignedNumber.h" namespace "pssp::ast":
    cpdef cppclass IExprSignedNumber(IExprNumber):
        const std_string &getImage()
        
        void setImage(const std_string & v)
        int32_t getWidth()
        
        void setWidth(int32_t v)
        int64_t getValue()
        
        void setValue(int64_t v)

cdef extern from "pssp/ast/IExprTemplateString.h" namespace "pssp::ast":
    cpdef cppclass IExprTemplateString(IExprString):
        ITemplateString *getTemplate()
        
        void setTemplate(ITemplateString *v)

cdef extern from "pssp/ast/IExprUnsignedNumber.h" namespace "pssp::ast":
    cpdef cppclass IExprUnsignedNumber(IExprNumber):
        const std_string &getImage()
        
        void setImage(const std_string & v)
        int32_t getWidth()
        
        void setWidth(int32_t v)
        uint64_t getValue()
        
        void setValue(uint64_t v)

cdef extern from "pssp/ast/IExtendType.h" namespace "pssp::ast":
    cpdef cppclass IExtendType(IScope):
        ExtendTargetE getKind()
        
        void setKind(ExtendTargetE v)
        ITypeIdentifier *getTarget()
        
        void setTarget(ITypeIdentifier *v)
        std_unordered_map[std_string,int32_t] &getSymtab()
        ISymbolImportSpec *getImports()
        
        void setImports(ISymbolImportSpec *v)

cdef extern from "pssp/ast/IField.h" namespace "pssp::ast":
    cpdef cppclass IField(INamedScopeChild):
        IDataType *getType()
        
        void setType(IDataType *v)
        FieldAttr getAttr()
        
        void setAttr(FieldAttr v)
        IExpr *getInit()
        
        void setInit(IExpr *v)

cdef extern from "pssp/ast/IFieldClaim.h" namespace "pssp::ast":
    cpdef cppclass IFieldClaim(INamedScopeChild):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)
        bool getIs_lock()
        
        void setIs_lock(bool v)

cdef extern from "pssp/ast/IFieldCompRef.h" namespace "pssp::ast":
    cpdef cppclass IFieldCompRef(INamedScopeChild):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)

cdef extern from "pssp/ast/IFieldPool.h" namespace "pssp::ast":
    cpdef cppclass IFieldPool(INamedScopeChild):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)
        IExpr *getSize()
        
        void setSize(IExpr *v)

cdef extern from "pssp/ast/IFieldRef.h" namespace "pssp::ast":
    cpdef cppclass IFieldRef(INamedScopeChild):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)
        bool getIs_input()
        
        void setIs_input(bool v)

cdef extern from "pssp/ast/IFunctionImportProto.h" namespace "pssp::ast":
    cpdef cppclass IFunctionImportProto(IFunctionImport):
        IFunctionPrototype *getProto()
        
        void setProto(IFunctionPrototype *v)

cdef extern from "pssp/ast/IFunctionImportType.h" namespace "pssp::ast":
    cpdef cppclass IFunctionImportType(IFunctionImport):
        ITypeIdentifier *getType()
        
        void setType(ITypeIdentifier *v)

cdef extern from "pssp/ast/IFunctionPrototype.h" namespace "pssp::ast":
    cpdef cppclass IFunctionPrototype(INamedScopeChild):
        IDataType *getRtype()
        
        void setRtype(IDataType *v)
        std_vector[UP[IFunctionParamDecl]] & getParameters();
        bool getIs_pure()
        
        void setIs_pure(bool v)
        bool getIs_target()
        
        void setIs_target(bool v)
        bool getIs_solve()
        
        void setIs_solve(bool v)
        bool getIs_core()
        
        void setIs_core(bool v)
        bool getIs_static()
        
        void setIs_static(bool v)

cdef extern from "pssp/ast/IGlobalScope.h" namespace "pssp::ast":
    cpdef cppclass IGlobalScope(IScope):
        int32_t getFileid()
        
        void setFileid(int32_t v)
        const std_string &getFilename()
        
        void setFilename(const std_string & v)

cdef extern from "pssp/ast/IInstanceOverride.h" namespace "pssp::ast":
    cpdef cppclass IInstanceOverride(IOverrideStmt):
        IExprHierarchicalId *getTarget()
        
        void setTarget(IExprHierarchicalId *v)
        ITypeIdentifier *getWith_t()
        
        void setWith_t(ITypeIdentifier *v)

cdef extern from "pssp/ast/IMonitorActivityLabeledStmt.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivityLabeledStmt(IMonitorActivityStmt):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "pssp/ast/IMonitorConstraint.h" namespace "pssp::ast":
    cpdef cppclass IMonitorConstraint(IMonitorActivityStmt):
        IConstraintStmt *getConstraint()
        
        void setConstraint(IConstraintStmt *v)

cdef extern from "pssp/ast/INamedScope.h" namespace "pssp::ast":
    cpdef cppclass INamedScope(IScope):
        IExprId *getName()
        
        void setName(IExprId *v)

cdef extern from "pssp/ast/IOverrideDecl.h" namespace "pssp::ast":
    cpdef cppclass IOverrideDecl(IScope):
        pass

cdef extern from "pssp/ast/IPackageScope.h" namespace "pssp::ast":
    cpdef cppclass IPackageScope(IScope):
        std_vector[UP[IExprId]] & getId();
        IPackageScopeP getSibling();
        
        void setSibling(IPackageScopeP v)

cdef extern from "pssp/ast/IProceduralStmtAssignment.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtAssignment(IExecStmt):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        AssignOp getOp()
        
        void setOp(AssignOp v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "pssp/ast/IProceduralStmtBody.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtBody(IExecStmt):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IProceduralStmtBreak.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtBreak(IExecStmt):
        pass

cdef extern from "pssp/ast/IProceduralStmtContinue.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtContinue(IExecStmt):
        pass

cdef extern from "pssp/ast/IProceduralStmtDataDeclaration.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtDataDeclaration(IExecStmt):
        IExprId *getName()
        
        void setName(IExprId *v)
        IDataType *getDatatype()
        
        void setDatatype(IDataType *v)
        IExpr *getInit()
        
        void setInit(IExpr *v)

cdef extern from "pssp/ast/IProceduralStmtExpr.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtExpr(IExecStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IProceduralStmtIfElse.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtIfElse(IExecStmt):
        std_vector[UP[IProceduralStmtIfClause]] & getIf_then();
        IScopeChild *getElse_then()
        
        void setElse_then(IScopeChild *v)

cdef extern from "pssp/ast/IProceduralStmtMatch.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtMatch(IExecStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        std_vector[UP[IProceduralStmtMatchChoice]] & getChoices();

cdef extern from "pssp/ast/IProceduralStmtMatchChoice.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtMatchChoice(IExecStmt):
        bool getIs_default()
        
        void setIs_default(bool v)
        IExprOpenRangeList *getCond()
        
        void setCond(IExprOpenRangeList *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IProceduralStmtRandomize.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtRandomize(IExecStmt):
        IExpr *getTarget()
        
        void setTarget(IExpr *v)
        std_vector[UP[IConstraintStmt]] & getConstraints();

cdef extern from "pssp/ast/IProceduralStmtReturn.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtReturn(IExecStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IProceduralStmtSuper.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtSuper(IExecStmt):
        pass

cdef extern from "pssp/ast/IProceduralStmtYield.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtYield(IExecStmt):
        pass

cdef extern from "pssp/ast/ISymbolChildrenScope.h" namespace "pssp::ast":
    cpdef cppclass ISymbolChildrenScope(ISymbolChild):
        const std_string &getName()
        
        void setName(const std_string & v)
        std_vector[UP[IScopeChild]] & getChildren();
        IScopeChildP getTarget();
        
        void setTarget(IScopeChildP v)

cdef extern from "pssp/ast/ITemplateCategoryTypeParamDecl.h" namespace "pssp::ast":
    cpdef cppclass ITemplateCategoryTypeParamDecl(ITemplateParamDecl):
        TypeCategory getCategory()
        
        void setCategory(TypeCategory v)
        ITypeIdentifier *getRestriction()
        
        void setRestriction(ITypeIdentifier *v)
        IDataType *getDflt()
        
        void setDflt(IDataType *v)

cdef extern from "pssp/ast/ITemplateGenericTypeParamDecl.h" namespace "pssp::ast":
    cpdef cppclass ITemplateGenericTypeParamDecl(ITemplateParamDecl):
        IDataType *getDflt()
        
        void setDflt(IDataType *v)

cdef extern from "pssp/ast/ITemplateValueParamDecl.h" namespace "pssp::ast":
    cpdef cppclass ITemplateValueParamDecl(ITemplateParamDecl):
        IDataType *getType()
        
        void setType(IDataType *v)
        IExpr *getDflt()
        
        void setDflt(IExpr *v)

cdef extern from "pssp/ast/ITypeOverride.h" namespace "pssp::ast":
    cpdef cppclass ITypeOverride(IOverrideStmt):
        ITypeIdentifier *getTarget()
        
        void setTarget(ITypeIdentifier *v)
        ITypeIdentifier *getWith_t()
        
        void setWith_t(ITypeIdentifier *v)

cdef extern from "pssp/ast/IActivityActionHandleTraversal.h" namespace "pssp::ast":
    cpdef cppclass IActivityActionHandleTraversal(IActivityLabeledStmt):
        IExprRefPathContext *getTarget()
        
        void setTarget(IExprRefPathContext *v)
        IConstraintStmt *getWith_c()
        
        void setWith_c(IConstraintStmt *v)
        std_vector[UP[IActionFieldInitializer]] & getInitializers();

cdef extern from "pssp/ast/IActivityActionTypeTraversal.h" namespace "pssp::ast":
    cpdef cppclass IActivityActionTypeTraversal(IActivityLabeledStmt):
        IDataTypeUserDefined *getTarget()
        
        void setTarget(IDataTypeUserDefined *v)
        IConstraintStmt *getWith_c()
        
        void setWith_c(IConstraintStmt *v)
        std_vector[UP[IActionFieldInitializer]] & getInitializers();

cdef extern from "pssp/ast/IActivityAtomicBlock.h" namespace "pssp::ast":
    cpdef cppclass IActivityAtomicBlock(IActivityLabeledStmt):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IActivityForeach.h" namespace "pssp::ast":
    cpdef cppclass IActivityForeach(IActivityLabeledStmt):
        IExprId *getIt_id()
        
        void setIt_id(IExprId *v)
        IExprId *getIdx_id()
        
        void setIdx_id(IExprId *v)
        IExprRefPathContext *getTarget()
        
        void setTarget(IExprRefPathContext *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IActivityIfElse.h" namespace "pssp::ast":
    cpdef cppclass IActivityIfElse(IActivityLabeledStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IScopeChild *getTrue_s()
        
        void setTrue_s(IScopeChild *v)
        IScopeChild *getFalse_s()
        
        void setFalse_s(IScopeChild *v)

cdef extern from "pssp/ast/IActivityMatch.h" namespace "pssp::ast":
    cpdef cppclass IActivityMatch(IActivityLabeledStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        std_vector[UP[IActivityMatchChoice]] & getChoices();

cdef extern from "pssp/ast/IMonitorActivityEventually.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivityEventually(IMonitorActivityLabeledStmt):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IActivityRepeatCount.h" namespace "pssp::ast":
    cpdef cppclass IActivityRepeatCount(IActivityLabeledStmt):
        IExprId *getLoop_var()
        
        void setLoop_var(IExprId *v)
        IExpr *getCount()
        
        void setCount(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IActivityRepeatWhile.h" namespace "pssp::ast":
    cpdef cppclass IActivityRepeatWhile(IActivityLabeledStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IActivityReplicate.h" namespace "pssp::ast":
    cpdef cppclass IActivityReplicate(IActivityLabeledStmt):
        IExprId *getIdx_id()
        
        void setIdx_id(IExprId *v)
        IExpr *getCount()
        
        void setCount(IExpr *v)
        IExprId *getIt_label()
        
        void setIt_label(IExprId *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IActivitySelect.h" namespace "pssp::ast":
    cpdef cppclass IActivitySelect(IActivityLabeledStmt):
        std_vector[UP[IActivitySelectBranch]] & getBranches();

cdef extern from "pssp/ast/IActivitySuper.h" namespace "pssp::ast":
    cpdef cppclass IActivitySuper(IActivityLabeledStmt):
        pass

cdef extern from "pssp/ast/IConstraintBlock.h" namespace "pssp::ast":
    cpdef cppclass IConstraintBlock(IConstraintScope):
        const std_string &getName()
        
        void setName(const std_string & v)
        bool getIs_dynamic()
        
        void setIs_dynamic(bool v)

cdef extern from "pssp/ast/IProceduralStmtRepeatWhile.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtRepeatWhile(IProceduralStmtBody):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IConstraintStmtForall.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtForall(IConstraintScope):
        IExprId *getIterator_id()
        
        void setIterator_id(IExprId *v)
        IDataTypeUserDefined *getType_id()
        
        void setType_id(IDataTypeUserDefined *v)
        IExprRefPath *getRef_path()
        
        void setRef_path(IExprRefPath *v)
        IConstraintSymbolScope *getSymtab()
        
        void setSymtab(IConstraintSymbolScope *v)

cdef extern from "pssp/ast/IConstraintStmtForeach.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtForeach(IConstraintScope):
        IConstraintStmtFieldP getIt();
        
        void setIt(IConstraintStmtFieldP v)
        IConstraintStmtFieldP getIdx();
        
        void setIdx(IConstraintStmtFieldP v)
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        IConstraintSymbolScope *getSymtab()
        
        void setSymtab(IConstraintSymbolScope *v)

cdef extern from "pssp/ast/IProceduralStmtWhile.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtWhile(IProceduralStmtBody):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IConstraintStmtImplication.h" namespace "pssp::ast":
    cpdef cppclass IConstraintStmtImplication(IConstraintScope):
        IExpr *getCond()
        
        void setCond(IExpr *v)

cdef extern from "pssp/ast/ISymbolScope.h" namespace "pssp::ast":
    cpdef cppclass ISymbolScope(ISymbolChildrenScope):
        std_unordered_map[std_string,int32_t] &getSymtab()
        ISymbolImportSpec *getImports()
        
        void setImports(ISymbolImportSpec *v)
        bool getSynthetic()
        
        void setSynthetic(bool v)
        bool getOpaque()
        
        void setOpaque(bool v)

cdef extern from "pssp/ast/ITypeScope.h" namespace "pssp::ast":
    cpdef cppclass ITypeScope(INamedScope):
        ITypeIdentifier *getSuper_t()
        
        void setSuper_t(ITypeIdentifier *v)
        ITemplateParamDeclList *getParams()
        
        void setParams(ITemplateParamDeclList *v)
        bool getOpaque()
        
        void setOpaque(bool v)

cdef extern from "pssp/ast/IExprRefPathSuper.h" namespace "pssp::ast":
    cpdef cppclass IExprRefPathSuper(IExprRefPathContext):
        pass

cdef extern from "pssp/ast/IAction.h" namespace "pssp::ast":
    cpdef cppclass IAction(ITypeScope):
        bool getIs_abstract()
        
        void setIs_abstract(bool v)
        bool getIs_override()
        
        void setIs_override(bool v)

cdef extern from "pssp/ast/IActivityDecl.h" namespace "pssp::ast":
    cpdef cppclass IActivityDecl(ISymbolScope):
        pass

cdef extern from "pssp/ast/IGenericConstraintDeclBool.h" namespace "pssp::ast":
    cpdef cppclass IGenericConstraintDeclBool(IConstraintBlock):
        bool getIs_static()
        
        void setIs_static(bool v)
        std_vector[UP[IGenericConstraintParam]] & getParameters();

cdef extern from "pssp/ast/IImportClass.h" namespace "pssp::ast":
    cpdef cppclass IImportClass(ITypeScope):
        std_vector[UP[ITypeIdentifier]] & getExtends();

cdef extern from "pssp/ast/IActivityLabeledScope.h" namespace "pssp::ast":
    cpdef cppclass IActivityLabeledScope(ISymbolScope):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "pssp/ast/IMonitor.h" namespace "pssp::ast":
    cpdef cppclass IMonitor(ITypeScope):
        bool getIs_abstract()
        
        void setIs_abstract(bool v)

cdef extern from "pssp/ast/IMonitorActivityDecl.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivityDecl(ISymbolScope):
        pass

cdef extern from "pssp/ast/IMonitorActivityLabeledScope.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivityLabeledScope(ISymbolScope):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "pssp/ast/IAnnotationDecl.h" namespace "pssp::ast":
    cpdef cppclass IAnnotationDecl(ITypeScope):
        pass

cdef extern from "pssp/ast/IComponent.h" namespace "pssp::ast":
    cpdef cppclass IComponent(ITypeScope):
        bool getIs_pure()
        
        void setIs_pure(bool v)

cdef extern from "pssp/ast/IProceduralStmtSymbolBodyScope.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtSymbolBodyScope(ISymbolScope):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "pssp/ast/IConstraintSymbolScope.h" namespace "pssp::ast":
    cpdef cppclass IConstraintSymbolScope(ISymbolScope):
        IConstraintStmtP getConstraint();
        
        void setConstraint(IConstraintStmtP v)

cdef extern from "pssp/ast/IRootSymbolScope.h" namespace "pssp::ast":
    cpdef cppclass IRootSymbolScope(ISymbolScope):
        std_vector[UP[IGlobalScope]] & getUnits();
        std_unordered_map[int32_t,std_string] &getFilenames()
        std_unordered_map[int32_t,int32_t] &getId2idx()
        std_vector[std_vector[int32_t]] & getFileOutRef();
        std_vector[std_vector[int32_t]] & getFileInRef();

cdef extern from "pssp/ast/IStruct.h" namespace "pssp::ast":
    cpdef cppclass IStruct(ITypeScope):
        StructKind getKind()
        
        void setKind(StructKind v)

cdef extern from "pssp/ast/ISymbolDeclaration.h" namespace "pssp::ast":
    cpdef cppclass ISymbolDeclaration(ISymbolScope):
        std_vector[UP[IFunctionParamDecl]] & getParams();

cdef extern from "pssp/ast/ISymbolEnumScope.h" namespace "pssp::ast":
    cpdef cppclass ISymbolEnumScope(ISymbolScope):
        pass

cdef extern from "pssp/ast/ISymbolExtendScope.h" namespace "pssp::ast":
    cpdef cppclass ISymbolExtendScope(ISymbolScope):
        pass

cdef extern from "pssp/ast/ICovergroupType.h" namespace "pssp::ast":
    cpdef cppclass ICovergroupType(ITypeScope):
        std_vector[UP[ICovergroupCoverpoint]] & getCoverpoints();
        std_vector[UP[ICovergroupCross]] & getCrosses();
        std_vector[UP[ICovergroupOption]] & getOptions();

cdef extern from "pssp/ast/ISymbolFunctionScope.h" namespace "pssp::ast":
    cpdef cppclass ISymbolFunctionScope(ISymbolScope):
        std_vector[IFunctionPrototypeP] & getPrototypes();
        std_vector[UP[IFunctionImport]] & getImport_specs();
        IFunctionDefinitionP getDefinition();
        
        void setDefinition(IFunctionDefinitionP v)
        ISymbolScope *getPlist()
        
        void setPlist(ISymbolScope *v)
        IExecScopeP getBody();
        
        void setBody(IExecScopeP v)

cdef extern from "pssp/ast/ISymbolTypeScope.h" namespace "pssp::ast":
    cpdef cppclass ISymbolTypeScope(ISymbolScope):
        ISymbolScope *getPlist()
        
        void setPlist(ISymbolScope *v)
        std_vector[UP[ISymbolTypeScope]] & getSpec_types();

cdef extern from "pssp/ast/ITemplateElem.h" namespace "pssp::ast":
    cpdef cppclass ITemplateElem(ISymbolScope):
        int32_t getOffset()
        
        void setOffset(int32_t v)
        int32_t getExtent()
        
        void setExtent(int32_t v)
        bool getIs_own_line()
        
        void setIs_own_line(bool v)

cdef extern from "pssp/ast/IExecScope.h" namespace "pssp::ast":
    cpdef cppclass IExecScope(ISymbolScope):
        pass

cdef extern from "pssp/ast/ITemplateString.h" namespace "pssp::ast":
    cpdef cppclass ITemplateString(ISymbolScope):
        const std_string &getRaw()
        
        void setRaw(const std_string & v)
        std_vector[UP[ITemplateElem]] & getElems();
        bool getIs_const()
        
        void setIs_const(bool v)

cdef extern from "pssp/ast/ITemplateText.h" namespace "pssp::ast":
    cpdef cppclass ITemplateText(ITemplateElem):
        const std_string &getText()
        
        void setText(const std_string & v)

cdef extern from "pssp/ast/ITemplateAssign.h" namespace "pssp::ast":
    cpdef cppclass ITemplateAssign(ITemplateElem):
        IExprId *getLhs()
        
        void setLhs(IExprId *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "pssp/ast/IProceduralStmtForeach.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtForeach(IProceduralStmtSymbolBodyScope):
        IExprRefPath *getPath()
        
        void setPath(IExprRefPath *v)
        IExprId *getIt_id()
        
        void setIt_id(IExprId *v)
        IExprId *getIdx_id()
        
        void setIdx_id(IExprId *v)

cdef extern from "pssp/ast/ITemplateBlock.h" namespace "pssp::ast":
    cpdef cppclass ITemplateBlock(ITemplateElem):
        std_vector[UP[ITemplateElem]] & getBody();

cdef extern from "pssp/ast/ITemplateComment.h" namespace "pssp::ast":
    cpdef cppclass ITemplateComment(ITemplateElem):
        const std_string &getText()
        
        void setText(const std_string & v)
        bool getIs_line()
        
        void setIs_line(bool v)

cdef extern from "pssp/ast/ITemplateExpr.h" namespace "pssp::ast":
    cpdef cppclass ITemplateExpr(ITemplateElem):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "pssp/ast/IProceduralStmtRepeat.h" namespace "pssp::ast":
    cpdef cppclass IProceduralStmtRepeat(IProceduralStmtSymbolBodyScope):
        IExprId *getIt_id()
        
        void setIt_id(IExprId *v)
        IExpr *getCount()
        
        void setCount(IExpr *v)

cdef extern from "pssp/ast/ITemplateIf.h" namespace "pssp::ast":
    cpdef cppclass ITemplateIf(ITemplateElem):
        std_vector[UP[ITemplateIfClause]] & getClauses();

cdef extern from "pssp/ast/IExecBlock.h" namespace "pssp::ast":
    cpdef cppclass IExecBlock(IExecScope):
        ExecKind getKind()
        
        void setKind(ExecKind v)

cdef extern from "pssp/ast/IMonitorActivityConcat.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivityConcat(IMonitorActivityLabeledScope):
        pass

cdef extern from "pssp/ast/IActivityParallel.h" namespace "pssp::ast":
    cpdef cppclass IActivityParallel(IActivityLabeledScope):
        IActivityJoinSpec *getJoin_spec()
        
        void setJoin_spec(IActivityJoinSpec *v)

cdef extern from "pssp/ast/IMonitorActivityOverlap.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivityOverlap(IMonitorActivityLabeledScope):
        pass

cdef extern from "pssp/ast/IMonitorActivitySchedule.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivitySchedule(IMonitorActivityLabeledScope):
        pass

cdef extern from "pssp/ast/IActivitySchedule.h" namespace "pssp::ast":
    cpdef cppclass IActivitySchedule(IActivityLabeledScope):
        IActivityJoinSpec *getJoin_spec()
        
        void setJoin_spec(IActivityJoinSpec *v)

cdef extern from "pssp/ast/IMonitorActivitySequence.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivitySequence(IMonitorActivityLabeledScope):
        pass

cdef extern from "pssp/ast/ITemplateVarDecl.h" namespace "pssp::ast":
    cpdef cppclass ITemplateVarDecl(ITemplateElem):
        std_vector[UP[IProceduralStmtDataDeclaration]] & getDecls();

cdef extern from "pssp/ast/IActivitySequence.h" namespace "pssp::ast":
    cpdef cppclass IActivitySequence(IActivityLabeledScope):
        pass

cdef extern from "pssp/ast/IMonitorActivitySelect.h" namespace "pssp::ast":
    cpdef cppclass IMonitorActivitySelect(IMonitorActivityLabeledScope):
        pass

cdef extern from "pssp/ast/ITemplateIfClause.h" namespace "pssp::ast":
    cpdef cppclass ITemplateIfClause(ITemplateBlock):
        IExpr *getCond()
        
        void setCond(IExpr *v)

cdef extern from "pssp/ast/ITemplateForeach.h" namespace "pssp::ast":
    cpdef cppclass ITemplateForeach(ITemplateBlock):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        IExprId *getIt()
        
        void setIt(IExprId *v)
        IExprId *getIdx()
        
        void setIdx(IExprId *v)

cdef extern from "pssp/ast/ITemplateRepeat.h" namespace "pssp::ast":
    cpdef cppclass ITemplateRepeat(ITemplateBlock):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        IExprId *getIdx()
        
        void setIdx(IExprId *v)

cdef extern from 'pssp/ast/impl/VisitorBase.h' namespace 'pssp::ast':
    cpdef cppclass VisitorBase:
        void visitSymbolImportSpec(ISymbolImportSpecP i)
        void visitAssocData(IAssocDataP i)
        void visitSymbolRefPath(ISymbolRefPathP i)
        void visitTemplateParamDeclList(ITemplateParamDeclListP i)
        void visitActivityMatchChoice(IActivityMatchChoiceP i)
        void visitTemplateParamValue(ITemplateParamValueP i)
        void visitTemplateParamValueList(ITemplateParamValueListP i)
        void visitExpr(IExprP i)
        void visitScopeChild(IScopeChildP i)
        void visitActivitySelectBranch(IActivitySelectBranchP i)
        void visitExprAggrMapElem(IExprAggrMapElemP i)
        void visitExprAggrStructElem(IExprAggrStructElemP i)
        void visitActionFieldInitializer(IActionFieldInitializerP i)
        void visitFunctionDefinition(IFunctionDefinitionP i)
        void visitFunctionImport(IFunctionImportP i)
        void visitFunctionParamDecl(IFunctionParamDeclP i)
        void visitTypedefDeclaration(ITypedefDeclarationP i)
        void visitGenericConstraintDeclValue(IGenericConstraintDeclValueP i)
        void visitActivityJoinSpec(IActivityJoinSpecP i)
        void visitGenericConstraintParam(IGenericConstraintParamP i)
        void visitMethodParameterList(IMethodParameterListP i)
        void visitActivitySchedulingConstraint(IActivitySchedulingConstraintP i)
        void visitMonitorActivityStmt(IMonitorActivityStmtP i)
        void visitActivityStmt(IActivityStmtP i)
        void visitNamedScopeChild(INamedScopeChildP i)
        void visitOverrideStmt(IOverrideStmtP i)
        void visitAnnotation(IAnnotationP i)
        void visitPackageImportStmt(IPackageImportStmtP i)
        void visitAnnotationParam(IAnnotationParamP i)
        void visitComment(ICommentP i)
        void visitComponentBind(IComponentBindP i)
        void visitComponentBindTarget(IComponentBindTargetP i)
        void visitComponentPathElem(IComponentPathElemP i)
        void visitProceduralStmtIfClause(IProceduralStmtIfClauseP i)
        void visitConstraintStmt(IConstraintStmtP i)
        void visitPyImportFromStmt(IPyImportFromStmtP i)
        void visitPyImportStmt(IPyImportStmtP i)
        void visitScope(IScopeP i)
        void visitCoverStmtReference(ICoverStmtReferenceP i)
        void visitScopeChildRef(IScopeChildRefP i)
        void visitSymbolChild(ISymbolChildP i)
        void visitCovergroupOption(ICovergroupOptionP i)
        void visitCovergroupPortmap(ICovergroupPortmapP i)
        void visitDataType(IDataTypeP i)
        void visitTargetTemplateFunction(ITargetTemplateFunctionP i)
        void visitDistItem(IDistItemP i)
        void visitDistWeight(IDistWeightP i)
        void visitTemplateParamDecl(ITemplateParamDeclP i)
        void visitExecBlockTag(IExecBlockTagP i)
        void visitTemplateParamExprValue(ITemplateParamExprValueP i)
        void visitExecStmt(IExecStmtP i)
        void visitExecTargetTemplateBlock(IExecTargetTemplateBlockP i)
        void visitExportAction(IExportActionP i)
        void visitExportFunction(IExportFunctionP i)
        void visitTemplateParamTypeValue(ITemplateParamTypeValueP i)
        void visitExprAggrLiteral(IExprAggrLiteralP i)
        void visitTypeIdentifier(ITypeIdentifierP i)
        void visitTypeIdentifierElem(ITypeIdentifierElemP i)
        void visitExprBin(IExprBinP i)
        void visitExprBitSlice(IExprBitSliceP i)
        void visitExprBool(IExprBoolP i)
        void visitExprCast(IExprCastP i)
        void visitExprCompileHas(IExprCompileHasP i)
        void visitExprCond(IExprCondP i)
        void visitExprDomainOpenRangeList(IExprDomainOpenRangeListP i)
        void visitExprDomainOpenRangeValue(IExprDomainOpenRangeValueP i)
        void visitExprFloatLiteral(IExprFloatLiteralP i)
        void visitExprHierarchicalId(IExprHierarchicalIdP i)
        void visitExprId(IExprIdP i)
        void visitExprIn(IExprInP i)
        void visitExprMemberPathElem(IExprMemberPathElemP i)
        void visitExprNull(IExprNullP i)
        void visitExprNumber(IExprNumberP i)
        void visitExprOpenRangeList(IExprOpenRangeListP i)
        void visitExprOpenRangeValue(IExprOpenRangeValueP i)
        void visitExprRefPath(IExprRefPathP i)
        void visitExprSliceRange(IExprSliceRangeP i)
        void visitExprString(IExprStringP i)
        void visitExprUnary(IExprUnaryP i)
        void visitExtendEnum(IExtendEnumP i)
        void visitActionHandleField(IActionHandleFieldP i)
        void visitActivityBindStmt(IActivityBindStmtP i)
        void visitActivityConstraint(IActivityConstraintP i)
        void visitActivityJoinSpecBranch(IActivityJoinSpecBranchP i)
        void visitActivityJoinSpecFirst(IActivityJoinSpecFirstP i)
        void visitActivityJoinSpecNone(IActivityJoinSpecNoneP i)
        void visitActivityJoinSpecSelect(IActivityJoinSpecSelectP i)
        void visitActivityLabeledStmt(IActivityLabeledStmtP i)
        void visitActivitySymbolCall(IActivitySymbolCallP i)
        void visitConstraintScope(IConstraintScopeP i)
        void visitConstraintStmtDefault(IConstraintStmtDefaultP i)
        void visitConstraintStmtDefaultDisable(IConstraintStmtDefaultDisableP i)
        void visitConstraintStmtDist(IConstraintStmtDistP i)
        void visitConstraintStmtExpr(IConstraintStmtExprP i)
        void visitConstraintStmtField(IConstraintStmtFieldP i)
        void visitConstraintStmtIf(IConstraintStmtIfP i)
        void visitConstraintStmtSoft(IConstraintStmtSoftP i)
        void visitConstraintStmtUnique(IConstraintStmtUniqueP i)
        void visitCoverStmtInline(ICoverStmtInlineP i)
        void visitCovergroup(ICovergroupP i)
        void visitCovergroupCoverpoint(ICovergroupCoverpointP i)
        void visitCovergroupCross(ICovergroupCrossP i)
        void visitCovergroupCrossBins(ICovergroupCrossBinsP i)
        void visitCovergroupInstantiation(ICovergroupInstantiationP i)
        void visitCoverpointBins(ICoverpointBinsP i)
        void visitDataTypeBool(IDataTypeBoolP i)
        void visitDataTypeChandle(IDataTypeChandleP i)
        void visitDataTypeEnum(IDataTypeEnumP i)
        void visitDataTypeFloat(IDataTypeFloatP i)
        void visitDataTypeInt(IDataTypeIntP i)
        void visitDataTypePyObj(IDataTypePyObjP i)
        void visitDataTypeRef(IDataTypeRefP i)
        void visitDataTypeString(IDataTypeStringP i)
        void visitDataTypeUserDefined(IDataTypeUserDefinedP i)
        void visitEnumDecl(IEnumDeclP i)
        void visitEnumItem(IEnumItemP i)
        void visitExprAggrEmpty(IExprAggrEmptyP i)
        void visitExprAggrList(IExprAggrListP i)
        void visitExprAggrMap(IExprAggrMapP i)
        void visitExprAggrStruct(IExprAggrStructP i)
        void visitExprRefPathContext(IExprRefPathContextP i)
        void visitExprRefPathStatic(IExprRefPathStaticP i)
        void visitExprRefPathStaticRooted(IExprRefPathStaticRootedP i)
        void visitExprSignedNumber(IExprSignedNumberP i)
        void visitExprTemplateString(IExprTemplateStringP i)
        void visitExprUnsignedNumber(IExprUnsignedNumberP i)
        void visitExtendType(IExtendTypeP i)
        void visitField(IFieldP i)
        void visitFieldClaim(IFieldClaimP i)
        void visitFieldCompRef(IFieldCompRefP i)
        void visitFieldPool(IFieldPoolP i)
        void visitFieldRef(IFieldRefP i)
        void visitFunctionImportProto(IFunctionImportProtoP i)
        void visitFunctionImportType(IFunctionImportTypeP i)
        void visitFunctionPrototype(IFunctionPrototypeP i)
        void visitGlobalScope(IGlobalScopeP i)
        void visitInstanceOverride(IInstanceOverrideP i)
        void visitMonitorActivityLabeledStmt(IMonitorActivityLabeledStmtP i)
        void visitMonitorConstraint(IMonitorConstraintP i)
        void visitNamedScope(INamedScopeP i)
        void visitOverrideDecl(IOverrideDeclP i)
        void visitPackageScope(IPackageScopeP i)
        void visitProceduralStmtAssignment(IProceduralStmtAssignmentP i)
        void visitProceduralStmtBody(IProceduralStmtBodyP i)
        void visitProceduralStmtBreak(IProceduralStmtBreakP i)
        void visitProceduralStmtContinue(IProceduralStmtContinueP i)
        void visitProceduralStmtDataDeclaration(IProceduralStmtDataDeclarationP i)
        void visitProceduralStmtExpr(IProceduralStmtExprP i)
        void visitProceduralStmtIfElse(IProceduralStmtIfElseP i)
        void visitProceduralStmtMatch(IProceduralStmtMatchP i)
        void visitProceduralStmtMatchChoice(IProceduralStmtMatchChoiceP i)
        void visitProceduralStmtRandomize(IProceduralStmtRandomizeP i)
        void visitProceduralStmtReturn(IProceduralStmtReturnP i)
        void visitProceduralStmtSuper(IProceduralStmtSuperP i)
        void visitProceduralStmtYield(IProceduralStmtYieldP i)
        void visitSymbolChildrenScope(ISymbolChildrenScopeP i)
        void visitTemplateCategoryTypeParamDecl(ITemplateCategoryTypeParamDeclP i)
        void visitTemplateGenericTypeParamDecl(ITemplateGenericTypeParamDeclP i)
        void visitTemplateValueParamDecl(ITemplateValueParamDeclP i)
        void visitTypeOverride(ITypeOverrideP i)
        void visitActivityActionHandleTraversal(IActivityActionHandleTraversalP i)
        void visitActivityActionTypeTraversal(IActivityActionTypeTraversalP i)
        void visitActivityAtomicBlock(IActivityAtomicBlockP i)
        void visitActivityForeach(IActivityForeachP i)
        void visitActivityIfElse(IActivityIfElseP i)
        void visitActivityMatch(IActivityMatchP i)
        void visitMonitorActivityEventually(IMonitorActivityEventuallyP i)
        void visitActivityRepeatCount(IActivityRepeatCountP i)
        void visitActivityRepeatWhile(IActivityRepeatWhileP i)
        void visitActivityReplicate(IActivityReplicateP i)
        void visitActivitySelect(IActivitySelectP i)
        void visitActivitySuper(IActivitySuperP i)
        void visitConstraintBlock(IConstraintBlockP i)
        void visitProceduralStmtRepeatWhile(IProceduralStmtRepeatWhileP i)
        void visitConstraintStmtForall(IConstraintStmtForallP i)
        void visitConstraintStmtForeach(IConstraintStmtForeachP i)
        void visitProceduralStmtWhile(IProceduralStmtWhileP i)
        void visitConstraintStmtImplication(IConstraintStmtImplicationP i)
        void visitSymbolScope(ISymbolScopeP i)
        void visitTypeScope(ITypeScopeP i)
        void visitExprRefPathSuper(IExprRefPathSuperP i)
        void visitAction(IActionP i)
        void visitActivityDecl(IActivityDeclP i)
        void visitGenericConstraintDeclBool(IGenericConstraintDeclBoolP i)
        void visitImportClass(IImportClassP i)
        void visitActivityLabeledScope(IActivityLabeledScopeP i)
        void visitMonitor(IMonitorP i)
        void visitMonitorActivityDecl(IMonitorActivityDeclP i)
        void visitMonitorActivityLabeledScope(IMonitorActivityLabeledScopeP i)
        void visitAnnotationDecl(IAnnotationDeclP i)
        void visitComponent(IComponentP i)
        void visitProceduralStmtSymbolBodyScope(IProceduralStmtSymbolBodyScopeP i)
        void visitConstraintSymbolScope(IConstraintSymbolScopeP i)
        void visitRootSymbolScope(IRootSymbolScopeP i)
        void visitStruct(IStructP i)
        void visitSymbolDeclaration(ISymbolDeclarationP i)
        void visitSymbolEnumScope(ISymbolEnumScopeP i)
        void visitSymbolExtendScope(ISymbolExtendScopeP i)
        void visitCovergroupType(ICovergroupTypeP i)
        void visitSymbolFunctionScope(ISymbolFunctionScopeP i)
        void visitSymbolTypeScope(ISymbolTypeScopeP i)
        void visitTemplateElem(ITemplateElemP i)
        void visitExecScope(IExecScopeP i)
        void visitTemplateString(ITemplateStringP i)
        void visitTemplateText(ITemplateTextP i)
        void visitTemplateAssign(ITemplateAssignP i)
        void visitProceduralStmtForeach(IProceduralStmtForeachP i)
        void visitTemplateBlock(ITemplateBlockP i)
        void visitTemplateComment(ITemplateCommentP i)
        void visitTemplateExpr(ITemplateExprP i)
        void visitProceduralStmtRepeat(IProceduralStmtRepeatP i)
        void visitTemplateIf(ITemplateIfP i)
        void visitExecBlock(IExecBlockP i)
        void visitMonitorActivityConcat(IMonitorActivityConcatP i)
        void visitActivityParallel(IActivityParallelP i)
        void visitMonitorActivityOverlap(IMonitorActivityOverlapP i)
        void visitMonitorActivitySchedule(IMonitorActivityScheduleP i)
        void visitActivitySchedule(IActivityScheduleP i)
        void visitMonitorActivitySequence(IMonitorActivitySequenceP i)
        void visitTemplateVarDecl(ITemplateVarDeclP i)
        void visitActivitySequence(IActivitySequenceP i)
        void visitMonitorActivitySelect(IMonitorActivitySelectP i)
        void visitTemplateIfClause(ITemplateIfClauseP i)
        void visitTemplateForeach(ITemplateForeachP i)
        void visitTemplateRepeat(ITemplateRepeatP i)
cdef extern from 'PyBaseVisitor.h' namespace 'pssp::ast':
    cpdef cppclass PyBaseVisitor(VisitorBase):
        PyBaseVisitor(cpy_ref.PyObject *)
        void py_acceptSymbolImportSpec(ISymbolImportSpec *i);
        void py_acceptAssocData(IAssocData *i);
        void py_acceptSymbolRefPath(ISymbolRefPath *i);
        void py_acceptTemplateParamDeclList(ITemplateParamDeclList *i);
        void py_acceptActivityMatchChoice(IActivityMatchChoice *i);
        void py_acceptTemplateParamValue(ITemplateParamValue *i);
        void py_acceptTemplateParamValueList(ITemplateParamValueList *i);
        void py_acceptExpr(IExpr *i);
        void py_acceptScopeChild(IScopeChild *i);
        void py_acceptActivitySelectBranch(IActivitySelectBranch *i);
        void py_acceptExprAggrMapElem(IExprAggrMapElem *i);
        void py_acceptExprAggrStructElem(IExprAggrStructElem *i);
        void py_visitSymbolImportSpecBase(ISymbolImportSpec *i)
        void py_visitAssocDataBase(IAssocData *i)
        void py_visitSymbolRefPathBase(ISymbolRefPath *i)
        void py_visitTemplateParamDeclListBase(ITemplateParamDeclList *i)
        void py_visitActivityMatchChoiceBase(IActivityMatchChoice *i)
        void py_visitTemplateParamValueBase(ITemplateParamValue *i)
        void py_visitTemplateParamValueListBase(ITemplateParamValueList *i)
        void py_visitExprBase(IExpr *i)
        void py_visitScopeChildBase(IScopeChild *i)
        void py_visitActivitySelectBranchBase(IActivitySelectBranch *i)
        void py_visitExprAggrMapElemBase(IExprAggrMapElem *i)
        void py_visitExprAggrStructElemBase(IExprAggrStructElem *i)
        void py_visitActionFieldInitializerBase(IActionFieldInitializer *i)
        void py_visitFunctionDefinitionBase(IFunctionDefinition *i)
        void py_visitFunctionImportBase(IFunctionImport *i)
        void py_visitFunctionParamDeclBase(IFunctionParamDecl *i)
        void py_visitTypedefDeclarationBase(ITypedefDeclaration *i)
        void py_visitGenericConstraintDeclValueBase(IGenericConstraintDeclValue *i)
        void py_visitActivityJoinSpecBase(IActivityJoinSpec *i)
        void py_visitGenericConstraintParamBase(IGenericConstraintParam *i)
        void py_visitMethodParameterListBase(IMethodParameterList *i)
        void py_visitActivitySchedulingConstraintBase(IActivitySchedulingConstraint *i)
        void py_visitMonitorActivityStmtBase(IMonitorActivityStmt *i)
        void py_visitActivityStmtBase(IActivityStmt *i)
        void py_visitNamedScopeChildBase(INamedScopeChild *i)
        void py_visitOverrideStmtBase(IOverrideStmt *i)
        void py_visitAnnotationBase(IAnnotation *i)
        void py_visitPackageImportStmtBase(IPackageImportStmt *i)
        void py_visitAnnotationParamBase(IAnnotationParam *i)
        void py_visitCommentBase(IComment *i)
        void py_visitComponentBindBase(IComponentBind *i)
        void py_visitComponentBindTargetBase(IComponentBindTarget *i)
        void py_visitComponentPathElemBase(IComponentPathElem *i)
        void py_visitProceduralStmtIfClauseBase(IProceduralStmtIfClause *i)
        void py_visitConstraintStmtBase(IConstraintStmt *i)
        void py_visitPyImportFromStmtBase(IPyImportFromStmt *i)
        void py_visitPyImportStmtBase(IPyImportStmt *i)
        void py_visitScopeBase(IScope *i)
        void py_visitCoverStmtReferenceBase(ICoverStmtReference *i)
        void py_visitScopeChildRefBase(IScopeChildRef *i)
        void py_visitSymbolChildBase(ISymbolChild *i)
        void py_visitCovergroupOptionBase(ICovergroupOption *i)
        void py_visitCovergroupPortmapBase(ICovergroupPortmap *i)
        void py_visitDataTypeBase(IDataType *i)
        void py_visitTargetTemplateFunctionBase(ITargetTemplateFunction *i)
        void py_visitDistItemBase(IDistItem *i)
        void py_visitDistWeightBase(IDistWeight *i)
        void py_visitTemplateParamDeclBase(ITemplateParamDecl *i)
        void py_visitExecBlockTagBase(IExecBlockTag *i)
        void py_visitTemplateParamExprValueBase(ITemplateParamExprValue *i)
        void py_visitExecStmtBase(IExecStmt *i)
        void py_visitExecTargetTemplateBlockBase(IExecTargetTemplateBlock *i)
        void py_visitExportActionBase(IExportAction *i)
        void py_visitExportFunctionBase(IExportFunction *i)
        void py_visitTemplateParamTypeValueBase(ITemplateParamTypeValue *i)
        void py_visitExprAggrLiteralBase(IExprAggrLiteral *i)
        void py_visitTypeIdentifierBase(ITypeIdentifier *i)
        void py_visitTypeIdentifierElemBase(ITypeIdentifierElem *i)
        void py_visitExprBinBase(IExprBin *i)
        void py_visitExprBitSliceBase(IExprBitSlice *i)
        void py_visitExprBoolBase(IExprBool *i)
        void py_visitExprCastBase(IExprCast *i)
        void py_visitExprCompileHasBase(IExprCompileHas *i)
        void py_visitExprCondBase(IExprCond *i)
        void py_visitExprDomainOpenRangeListBase(IExprDomainOpenRangeList *i)
        void py_visitExprDomainOpenRangeValueBase(IExprDomainOpenRangeValue *i)
        void py_visitExprFloatLiteralBase(IExprFloatLiteral *i)
        void py_visitExprHierarchicalIdBase(IExprHierarchicalId *i)
        void py_visitExprIdBase(IExprId *i)
        void py_visitExprInBase(IExprIn *i)
        void py_visitExprMemberPathElemBase(IExprMemberPathElem *i)
        void py_visitExprNullBase(IExprNull *i)
        void py_visitExprNumberBase(IExprNumber *i)
        void py_visitExprOpenRangeListBase(IExprOpenRangeList *i)
        void py_visitExprOpenRangeValueBase(IExprOpenRangeValue *i)
        void py_visitExprRefPathBase(IExprRefPath *i)
        void py_visitExprSliceRangeBase(IExprSliceRange *i)
        void py_visitExprStringBase(IExprString *i)
        void py_visitExprUnaryBase(IExprUnary *i)
        void py_visitExtendEnumBase(IExtendEnum *i)
        void py_visitActionHandleFieldBase(IActionHandleField *i)
        void py_visitActivityBindStmtBase(IActivityBindStmt *i)
        void py_visitActivityConstraintBase(IActivityConstraint *i)
        void py_visitActivityJoinSpecBranchBase(IActivityJoinSpecBranch *i)
        void py_visitActivityJoinSpecFirstBase(IActivityJoinSpecFirst *i)
        void py_visitActivityJoinSpecNoneBase(IActivityJoinSpecNone *i)
        void py_visitActivityJoinSpecSelectBase(IActivityJoinSpecSelect *i)
        void py_visitActivityLabeledStmtBase(IActivityLabeledStmt *i)
        void py_visitActivitySymbolCallBase(IActivitySymbolCall *i)
        void py_visitConstraintScopeBase(IConstraintScope *i)
        void py_visitConstraintStmtDefaultBase(IConstraintStmtDefault *i)
        void py_visitConstraintStmtDefaultDisableBase(IConstraintStmtDefaultDisable *i)
        void py_visitConstraintStmtDistBase(IConstraintStmtDist *i)
        void py_visitConstraintStmtExprBase(IConstraintStmtExpr *i)
        void py_visitConstraintStmtFieldBase(IConstraintStmtField *i)
        void py_visitConstraintStmtIfBase(IConstraintStmtIf *i)
        void py_visitConstraintStmtSoftBase(IConstraintStmtSoft *i)
        void py_visitConstraintStmtUniqueBase(IConstraintStmtUnique *i)
        void py_visitCoverStmtInlineBase(ICoverStmtInline *i)
        void py_visitCovergroupBase(ICovergroup *i)
        void py_visitCovergroupCoverpointBase(ICovergroupCoverpoint *i)
        void py_visitCovergroupCrossBase(ICovergroupCross *i)
        void py_visitCovergroupCrossBinsBase(ICovergroupCrossBins *i)
        void py_visitCovergroupInstantiationBase(ICovergroupInstantiation *i)
        void py_visitCoverpointBinsBase(ICoverpointBins *i)
        void py_visitDataTypeBoolBase(IDataTypeBool *i)
        void py_visitDataTypeChandleBase(IDataTypeChandle *i)
        void py_visitDataTypeEnumBase(IDataTypeEnum *i)
        void py_visitDataTypeFloatBase(IDataTypeFloat *i)
        void py_visitDataTypeIntBase(IDataTypeInt *i)
        void py_visitDataTypePyObjBase(IDataTypePyObj *i)
        void py_visitDataTypeRefBase(IDataTypeRef *i)
        void py_visitDataTypeStringBase(IDataTypeString *i)
        void py_visitDataTypeUserDefinedBase(IDataTypeUserDefined *i)
        void py_visitEnumDeclBase(IEnumDecl *i)
        void py_visitEnumItemBase(IEnumItem *i)
        void py_visitExprAggrEmptyBase(IExprAggrEmpty *i)
        void py_visitExprAggrListBase(IExprAggrList *i)
        void py_visitExprAggrMapBase(IExprAggrMap *i)
        void py_visitExprAggrStructBase(IExprAggrStruct *i)
        void py_visitExprRefPathContextBase(IExprRefPathContext *i)
        void py_visitExprRefPathStaticBase(IExprRefPathStatic *i)
        void py_visitExprRefPathStaticRootedBase(IExprRefPathStaticRooted *i)
        void py_visitExprSignedNumberBase(IExprSignedNumber *i)
        void py_visitExprTemplateStringBase(IExprTemplateString *i)
        void py_visitExprUnsignedNumberBase(IExprUnsignedNumber *i)
        void py_visitExtendTypeBase(IExtendType *i)
        void py_visitFieldBase(IField *i)
        void py_visitFieldClaimBase(IFieldClaim *i)
        void py_visitFieldCompRefBase(IFieldCompRef *i)
        void py_visitFieldPoolBase(IFieldPool *i)
        void py_visitFieldRefBase(IFieldRef *i)
        void py_visitFunctionImportProtoBase(IFunctionImportProto *i)
        void py_visitFunctionImportTypeBase(IFunctionImportType *i)
        void py_visitFunctionPrototypeBase(IFunctionPrototype *i)
        void py_visitGlobalScopeBase(IGlobalScope *i)
        void py_visitInstanceOverrideBase(IInstanceOverride *i)
        void py_visitMonitorActivityLabeledStmtBase(IMonitorActivityLabeledStmt *i)
        void py_visitMonitorConstraintBase(IMonitorConstraint *i)
        void py_visitNamedScopeBase(INamedScope *i)
        void py_visitOverrideDeclBase(IOverrideDecl *i)
        void py_visitPackageScopeBase(IPackageScope *i)
        void py_visitProceduralStmtAssignmentBase(IProceduralStmtAssignment *i)
        void py_visitProceduralStmtBodyBase(IProceduralStmtBody *i)
        void py_visitProceduralStmtBreakBase(IProceduralStmtBreak *i)
        void py_visitProceduralStmtContinueBase(IProceduralStmtContinue *i)
        void py_visitProceduralStmtDataDeclarationBase(IProceduralStmtDataDeclaration *i)
        void py_visitProceduralStmtExprBase(IProceduralStmtExpr *i)
        void py_visitProceduralStmtIfElseBase(IProceduralStmtIfElse *i)
        void py_visitProceduralStmtMatchBase(IProceduralStmtMatch *i)
        void py_visitProceduralStmtMatchChoiceBase(IProceduralStmtMatchChoice *i)
        void py_visitProceduralStmtRandomizeBase(IProceduralStmtRandomize *i)
        void py_visitProceduralStmtReturnBase(IProceduralStmtReturn *i)
        void py_visitProceduralStmtSuperBase(IProceduralStmtSuper *i)
        void py_visitProceduralStmtYieldBase(IProceduralStmtYield *i)
        void py_visitSymbolChildrenScopeBase(ISymbolChildrenScope *i)
        void py_visitTemplateCategoryTypeParamDeclBase(ITemplateCategoryTypeParamDecl *i)
        void py_visitTemplateGenericTypeParamDeclBase(ITemplateGenericTypeParamDecl *i)
        void py_visitTemplateValueParamDeclBase(ITemplateValueParamDecl *i)
        void py_visitTypeOverrideBase(ITypeOverride *i)
        void py_visitActivityActionHandleTraversalBase(IActivityActionHandleTraversal *i)
        void py_visitActivityActionTypeTraversalBase(IActivityActionTypeTraversal *i)
        void py_visitActivityAtomicBlockBase(IActivityAtomicBlock *i)
        void py_visitActivityForeachBase(IActivityForeach *i)
        void py_visitActivityIfElseBase(IActivityIfElse *i)
        void py_visitActivityMatchBase(IActivityMatch *i)
        void py_visitMonitorActivityEventuallyBase(IMonitorActivityEventually *i)
        void py_visitActivityRepeatCountBase(IActivityRepeatCount *i)
        void py_visitActivityRepeatWhileBase(IActivityRepeatWhile *i)
        void py_visitActivityReplicateBase(IActivityReplicate *i)
        void py_visitActivitySelectBase(IActivitySelect *i)
        void py_visitActivitySuperBase(IActivitySuper *i)
        void py_visitConstraintBlockBase(IConstraintBlock *i)
        void py_visitProceduralStmtRepeatWhileBase(IProceduralStmtRepeatWhile *i)
        void py_visitConstraintStmtForallBase(IConstraintStmtForall *i)
        void py_visitConstraintStmtForeachBase(IConstraintStmtForeach *i)
        void py_visitProceduralStmtWhileBase(IProceduralStmtWhile *i)
        void py_visitConstraintStmtImplicationBase(IConstraintStmtImplication *i)
        void py_visitSymbolScopeBase(ISymbolScope *i)
        void py_visitTypeScopeBase(ITypeScope *i)
        void py_visitExprRefPathSuperBase(IExprRefPathSuper *i)
        void py_visitActionBase(IAction *i)
        void py_visitActivityDeclBase(IActivityDecl *i)
        void py_visitGenericConstraintDeclBoolBase(IGenericConstraintDeclBool *i)
        void py_visitImportClassBase(IImportClass *i)
        void py_visitActivityLabeledScopeBase(IActivityLabeledScope *i)
        void py_visitMonitorBase(IMonitor *i)
        void py_visitMonitorActivityDeclBase(IMonitorActivityDecl *i)
        void py_visitMonitorActivityLabeledScopeBase(IMonitorActivityLabeledScope *i)
        void py_visitAnnotationDeclBase(IAnnotationDecl *i)
        void py_visitComponentBase(IComponent *i)
        void py_visitProceduralStmtSymbolBodyScopeBase(IProceduralStmtSymbolBodyScope *i)
        void py_visitConstraintSymbolScopeBase(IConstraintSymbolScope *i)
        void py_visitRootSymbolScopeBase(IRootSymbolScope *i)
        void py_visitStructBase(IStruct *i)
        void py_visitSymbolDeclarationBase(ISymbolDeclaration *i)
        void py_visitSymbolEnumScopeBase(ISymbolEnumScope *i)
        void py_visitSymbolExtendScopeBase(ISymbolExtendScope *i)
        void py_visitCovergroupTypeBase(ICovergroupType *i)
        void py_visitSymbolFunctionScopeBase(ISymbolFunctionScope *i)
        void py_visitSymbolTypeScopeBase(ISymbolTypeScope *i)
        void py_visitTemplateElemBase(ITemplateElem *i)
        void py_visitExecScopeBase(IExecScope *i)
        void py_visitTemplateStringBase(ITemplateString *i)
        void py_visitTemplateTextBase(ITemplateText *i)
        void py_visitTemplateAssignBase(ITemplateAssign *i)
        void py_visitProceduralStmtForeachBase(IProceduralStmtForeach *i)
        void py_visitTemplateBlockBase(ITemplateBlock *i)
        void py_visitTemplateCommentBase(ITemplateComment *i)
        void py_visitTemplateExprBase(ITemplateExpr *i)
        void py_visitProceduralStmtRepeatBase(IProceduralStmtRepeat *i)
        void py_visitTemplateIfBase(ITemplateIf *i)
        void py_visitExecBlockBase(IExecBlock *i)
        void py_visitMonitorActivityConcatBase(IMonitorActivityConcat *i)
        void py_visitActivityParallelBase(IActivityParallel *i)
        void py_visitMonitorActivityOverlapBase(IMonitorActivityOverlap *i)
        void py_visitMonitorActivityScheduleBase(IMonitorActivitySchedule *i)
        void py_visitActivityScheduleBase(IActivitySchedule *i)
        void py_visitMonitorActivitySequenceBase(IMonitorActivitySequence *i)
        void py_visitTemplateVarDeclBase(ITemplateVarDecl *i)
        void py_visitActivitySequenceBase(IActivitySequence *i)
        void py_visitMonitorActivitySelectBase(IMonitorActivitySelect *i)
        void py_visitTemplateIfClauseBase(ITemplateIfClause *i)
        void py_visitTemplateForeachBase(ITemplateForeach *i)
        void py_visitTemplateRepeatBase(ITemplateRepeat *i)
