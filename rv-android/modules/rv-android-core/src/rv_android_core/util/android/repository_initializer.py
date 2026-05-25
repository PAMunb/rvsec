from rv_android_core.domain.coverage import (
    ClassCoverageData,
    LogcatRepository,
    MethodCoverageData,
)
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


def initialize_repository_from_static_data(
    repository: LogcatRepository,
    static_data: StaticAnalysisData,
    component_name: str = "RepositoryInitializer",
) -> None:
    """
    Initialize LogcatRepository with static analysis data.

    Consolidates repository initialization logic to eliminate code duplication
    across multiple system components. Populates repository with class and
    method coverage data from static analysis results.

    ### Architectural Role:
    - Centralizes repository initialization patterns
    - Ensures consistent data population across components
    - Provides standardized error handling and logging
    - Maintains separation between static analysis and coverage tracking

    ### Integration Points:
    - Called by CoverageAnalyzer, CoverageTracker, PostProcessor, LogcatParser
    - Uses LoggingManager for consistent logging patterns
    - Integrates with static analysis data structures
    - Populates LogcatRepository for coverage tracking

    Args:
        repository: LogcatRepository instance to initialize
        static_data: Static analysis data containing class and method information
        component_name: Name of the component calling this function (for logging)
    """
    # Set up logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger(
        "rv_android_core.util.repository_initializer",
        {CONTEXT_COMPONENT: component_name},
    )

    logger.debug(
        f"Initializing repository with {len(static_data.classes.classes)} classes"
    )

    # Initialize repository with static analysis data
    for class_name, class_info in static_data.classes.classes.items():
        class_data = ClassCoverageData(
            name=class_name,
            component_type=class_info.component_type,
            is_main=getattr(class_info, "is_main", False),
        )
        repository.add_class(class_data)

        for method in class_info.methods:
            method_data = MethodCoverageData(
                class_name=method.class_name,
                method_name=method.name,
                signature=method.signature,
                parameters=method.params,
                reachable=method.reachable,
                reaches_target=method.reaches_target,
                directly_reaches_target=method.directly_reaches_target,
                from_static_analysis=True,
            )
            class_data.add_method(method_data)

    logger.debug("Repository initialized successfully")
