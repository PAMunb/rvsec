"""Tests for Components domain models."""

import pytest
from rv_android_core.domain.components import ComponentInfo, Components, IntentFilter


class TestIntentFilter:
    def test_initialization(self):
        f = IntentFilter(
            actions=["android.intent.action.MAIN"],
            categories=["android.intent.category.LAUNCHER"],
        )
        assert f.actions == ["android.intent.action.MAIN"]
        assert f.categories == ["android.intent.category.LAUNCHER"]

    def test_empty_defaults(self):
        f = IntentFilter()
        assert f.actions == []
        assert f.categories == []


class TestComponentInfo:
    def test_activity_with_intent_filters(self):
        f = IntentFilter(
            actions=["android.intent.action.MAIN"],
            categories=["android.intent.category.LAUNCHER"],
        )
        c = ComponentInfo(
            class_name="com.example.MainActivity",
            component_type="activity",
            is_main=True,
            intent_filters=[f],
            exported=True,
            reaches_target=False,
            target_methods=[],
        )
        assert c.class_name == "com.example.MainActivity"
        assert c.component_type == "activity"
        assert c.is_main is True
        assert len(c.intent_filters) == 1
        assert c.intent_filters[0].actions == ["android.intent.action.MAIN"]
        assert c.authorities is None
        assert c.exported is True
        assert c.reaches_target is False

    def test_provider_with_authorities(self):
        c = ComponentInfo(
            class_name="com.example.MyProvider",
            component_type="provider",
            authorities="com.example.provider",
            exported=False,
        )
        assert c.component_type == "provider"
        assert c.authorities == "com.example.provider"
        assert c.intent_filters == []
        assert c.is_main is False

    def test_service_with_mop(self):
        c = ComponentInfo(
            class_name="com.example.CryptoService",
            component_type="service",
            reaches_target=True,
            target_methods=["<com.example.CryptoService: void onStartCommand()>"],
        )
        assert c.reaches_target is True
        assert len(c.target_methods) == 1

    def test_defaults(self):
        c = ComponentInfo(class_name="com.example.Test", component_type="service")
        assert c.is_main is False
        assert c.intent_filters == []
        assert c.authorities is None
        assert c.exported is False
        assert c.reaches_target is False
        assert c.target_methods == []


class TestComponents:
    @pytest.fixture
    def sample_components(self):
        return Components(
            activities=[
                ComponentInfo(
                    class_name="com.example.MainActivity",
                    component_type="activity",
                    is_main=True,
                    exported=True,
                ),
                ComponentInfo(
                    class_name="com.example.DetailActivity",
                    component_type="activity",
                    exported=True,
                ),
            ],
            receivers=[
                ComponentInfo(
                    class_name="com.example.BootReceiver",
                    component_type="receiver",
                    exported=True,
                    reaches_target=True,
                    target_methods=["<com.example.BootReceiver: void onReceive()>"],
                ),
            ],
            services=[
                ComponentInfo(
                    class_name="com.example.CryptoService",
                    component_type="service",
                    reaches_target=True,
                    target_methods=[
                        "<com.example.CryptoService: void onStartCommand()>"
                    ],
                ),
            ],
            providers=[
                ComponentInfo(
                    class_name="com.example.DataProvider",
                    component_type="provider",
                    authorities="com.example.data",
                ),
            ],
        )

    def test_empty_components(self):
        c = Components()
        assert c.activities == []
        assert c.receivers == []
        assert c.services == []
        assert c.providers == []
        assert c.get_all() == []

    def test_get_by_type(self, sample_components):
        assert len(sample_components.get_by_type("activity")) == 2
        assert len(sample_components.get_by_type("receiver")) == 1
        assert len(sample_components.get_by_type("service")) == 1
        assert len(sample_components.get_by_type("provider")) == 1
        assert len(sample_components.get_by_type("unknown")) == 0

    def test_get_all(self, sample_components):
        assert len(sample_components.get_all()) == 5

    def test_get_mop_components(self, sample_components):
        mop = sample_components.get_mop_components()
        assert len(mop) == 2
        names = {c.class_name for c in mop}
        assert "com.example.BootReceiver" in names
        assert "com.example.CryptoService" in names

    def test_get_exported_components(self, sample_components):
        exported = sample_components.get_exported_components()
        assert len(exported) == 3  # 2 activities + 1 receiver

    def test_get_by_class_name(self, sample_components):
        c = sample_components.get_by_class_name("com.example.DataProvider")
        assert c is not None
        assert c.component_type == "provider"
        assert c.authorities == "com.example.data"

    def test_get_by_class_name_not_found(self, sample_components):
        assert sample_components.get_by_class_name("com.example.DoesNotExist") is None

    def test_get_analysis_summary(self, sample_components):
        summary = sample_components.get_analysis_summary()
        assert summary["activities"] == 2
        assert summary["receivers"] == 1
        assert summary["services"] == 1
        assert summary["providers"] == 1
        assert summary["total"] == 5
        assert summary["mop_components"] == 2
        assert summary["exported_components"] == 3
