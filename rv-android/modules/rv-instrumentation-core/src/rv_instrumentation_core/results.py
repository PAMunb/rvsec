from typing import Dict, Optional

from pydantic import Field, computed_field
from rv_android_core.util.validation.base import BaseValidatedModel


class InstrumentationError(BaseValidatedModel):
    """
    Structured representation of instrumentation pipeline errors.

    ### Architectural Decisions:
    - Provides consistent error structure for instrumentation failure tracking
    - Integrates with existing error handling and logging infrastructure
    - Supports detailed error classification for debugging and analysis
    - Enables automated error reporting and recovery strategies

    ### Role in the System:
    - Standardizes error information across instrumentation pipeline phases
    - Enables structured error logging and analysis for debugging
    - Supports automated error recovery and retry strategies
    - Provides consistent error interface for experiment orchestration
    """

    code: int = Field(..., description="Numeric error code for programmatic handling")
    tool: Optional[str] = Field(
        default=None, description="Name of tool that failed during execution"
    )
    message: str = Field(..., description="Human-readable error description")
    phase: str = Field(..., description="Pipeline phase where error occurred")


class InstrumentationResults(BaseValidatedModel):
    """
    Comprehensive results and metrics from instrumentation pipeline execution.

    ### Architectural Decisions:
    - Aggregates instrumentation outcomes for batch processing analysis
    - Provides computed metrics for success rate calculation and reporting
    - Structures error information for detailed failure analysis
    - Integrates with experiment orchestration for batch operation tracking

    ### Role in the System:
    - Tracks instrumentation success and failure metrics across batches
    - Provides structured data for experiment result analysis
    - Enables automated quality assessment of instrumentation operations
    - Supports debugging and optimization of instrumentation workflows
    """

    errors: Dict[str, InstrumentationError] = Field(
        default_factory=dict, description="Detailed error information keyed by APK name"
    )
    success_count: int = Field(
        default=0, ge=0, description="Number of successfully instrumented APKs"
    )
    total_count: int = Field(
        default=0, ge=0, description="Total number of APKs processed"
    )
    variant: str = Field(
        default="ajc",
        description=(
            "Instrumentation variant that produced this result: 'ajc' (legacy "
            "dex2jar+ajc+d8 pipeline) or 'dexlib2' (gh52 DEX-native pipeline). "
            "Tagged by the producing pipeline and consumed by downstream "
            "analysis/reporting. Legacy JSON without this field deserializes "
            "as 'ajc' to preserve backward compatibility."
        ),
    )

    @computed_field
    @property
    def success_rate(self) -> float:
        """
        Calculate instrumentation success rate as percentage.

        Returns:
            Success rate percentage (0.0 to 100.0)
        """
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100
