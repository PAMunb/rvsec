"""
Domain models for Android component representation in RV-Android Core.

This module provides validated models for representing Android components
(Activities, Services, Receivers, Providers) with their intent filters,
export status, and monitored operations reachability.
"""

from typing import Dict, List, Optional

from pydantic import Field
from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(["actions", "categories"])
class IntentFilter(BaseValidatedModel):
    """Intent filter with actions, categories and data block from AndroidManifest.xml.

    D15 (2026-05-29) — data fields exposed so downstream consumers
    (aperv, manual triggering) can construct Intents reaching deep-link
    or MIME-typed entry points. Empty lists are the back-compat default
    so pre-D15 JSONs parse unchanged.
    """

    actions: List[str] = Field(default_factory=list, description="Intent actions")
    categories: List[str] = Field(default_factory=list, description="Intent categories")
    data_schemes: List[str] = Field(
        default_factory=list, description="URI schemes (http, content, custom)"
    )
    data_hosts: List[str] = Field(
        default_factory=list, description="URI hosts"
    )
    data_ports: List[int] = Field(
        default_factory=list, description="URI ports (only declared ones, port>=0)"
    )
    data_paths: List[str] = Field(
        default_factory=list,
        description="Literal URI paths (android:path)",
    )
    data_path_prefixes: List[str] = Field(
        default_factory=list,
        description="Prefix URI paths (android:pathPrefix)",
    )
    data_path_patterns: List[str] = Field(
        default_factory=list,
        description="Glob URI paths (android:pathPattern)",
    )
    data_mime_types: List[str] = Field(
        default_factory=list, description="MIME types (e.g. text/plain, image/*)"
    )


@validated_model(["class_name", "component_type"])
class ComponentInfo(BaseValidatedModel):
    """Metadata for an Android component (Activity, Service, Receiver, or Provider)."""

    class_name: str = Field(..., description="Fully qualified class name", min_length=1)
    component_type: str = Field(
        ...,
        description="Component type: activity, service, receiver, provider",
    )
    is_main: bool = Field(
        default=False, description="True if this is the main launcher activity"
    )
    intent_filters: List[IntentFilter] = Field(
        default_factory=list, description="Intent filters from manifest"
    )
    authorities: Optional[str] = Field(
        default=None, description="Content provider authorities (providers only)"
    )
    exported: bool = Field(
        default=False, description="Whether the component is exported"
    )
    permission: Optional[str] = Field(
        default=None,
        description="android:permission attribute (None when undeclared) — D15",
    )
    reaches_target: bool = Field(
        default=False,
        description="Whether lifecycle methods reach monitored operations",
    )
    target_methods: List[str] = Field(
        default_factory=list,
        description="Signatures of lifecycle methods reaching MOP",
    )


class ProviderComponentInfo(ComponentInfo):
    """ContentProvider with granular read/write permissions (D15)."""

    read_permission: Optional[str] = Field(
        default=None,
        description="android:readPermission (overrides `permission` for reads)",
    )
    write_permission: Optional[str] = Field(
        default=None,
        description="android:writePermission (overrides `permission` for writes)",
    )


class Components(BaseValidatedModel):
    """Container for all Android component types parsed from the analysis JSON components{} section."""

    activities: List[ComponentInfo] = Field(default_factory=list)
    receivers: List[ComponentInfo] = Field(default_factory=list)
    services: List[ComponentInfo] = Field(default_factory=list)
    providers: List[ProviderComponentInfo] = Field(default_factory=list)

    def get_by_type(self, component_type: str) -> List[ComponentInfo]:
        """Return components of the given type."""
        type_map = {
            "activity": self.activities,
            "receiver": self.receivers,
            "service": self.services,
            "provider": self.providers,
        }
        return type_map.get(component_type, [])

    def get_all(self) -> List[ComponentInfo]:
        """Return all components across all types."""
        return self.activities + self.receivers + self.services + self.providers

    def get_mop_components(self) -> List[ComponentInfo]:
        """Return components that reach monitored operations."""
        return [c for c in self.get_all() if c.reaches_target]

    def get_exported_components(self) -> List[ComponentInfo]:
        """Return components that are exported."""
        return [c for c in self.get_all() if c.exported]

    def get_by_class_name(self, class_name: str) -> Optional[ComponentInfo]:
        """Find a component by class name across all types."""
        for c in self.get_all():
            if c.class_name == class_name:
                return c
        return None

    def get_analysis_summary(self) -> Dict:
        """Return a summary of component counts."""
        return {
            "activities": len(self.activities),
            "receivers": len(self.receivers),
            "services": len(self.services),
            "providers": len(self.providers),
            "total": len(self.get_all()),
            "mop_components": len(self.get_mop_components()),
            "exported_components": len(self.get_exported_components()),
        }
