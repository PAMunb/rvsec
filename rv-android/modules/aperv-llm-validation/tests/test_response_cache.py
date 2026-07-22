"""Tests for the SQLite response cache."""

import pytest

from aperv_llm_validation.infrastructure.response_cache import ResponseCache


@pytest.fixture
def cache(tmp_path):
    return ResponseCache(tmp_path / "test_cache")


SAMPLE_RESPONSE = {"choices": [{"message": {"content": "test"}}]}


class TestResponseCache:
    def test_put_get_round_trip(self, cache):
        cache.put("001.png", "ape_current", 42, 0.3, "max_edge",
                  SAMPLE_RESPONSE, 100, 50, 1500)
        result = cache.get("001.png", "ape_current", 42, 0.3, "max_edge")

        assert result is not None
        assert result["response"] == SAMPLE_RESPONSE
        assert result["tokens_in"] == 100
        assert result["tokens_out"] == 50
        assert result["latency_ms"] == 1500

    def test_cache_miss_returns_none(self, cache):
        result = cache.get("nonexistent.png", "ape_current", 42, 0.3, "max_edge")
        assert result is None

    def test_different_temperature_different_key(self, cache):
        """Temperature is part of cache key — different temps don't collide."""
        cache.put("001.png", "ape_current", 42, 0.01, "max_edge",
                  {"temp": "low"}, 100, 50, 1500)
        cache.put("001.png", "ape_current", 42, 0.7, "max_edge",
                  {"temp": "high"}, 100, 50, 1500)

        low = cache.get("001.png", "ape_current", 42, 0.01, "max_edge")
        high = cache.get("001.png", "ape_current", 42, 0.7, "max_edge")

        assert low["response"]["temp"] == "low"
        assert high["response"]["temp"] == "high"

    def test_different_resize_mode_different_key(self, cache):
        """Resize mode is part of cache key."""
        cache.put("001.png", "ape_current", 42, 0.3, "max_edge",
                  {"mode": "max_edge"}, 100, 50, 1500)
        cache.put("001.png", "ape_current", 42, 0.3, "smart_resize",
                  {"mode": "smart_resize"}, 100, 50, 1500)

        me = cache.get("001.png", "ape_current", 42, 0.3, "max_edge")
        sr = cache.get("001.png", "ape_current", 42, 0.3, "smart_resize")

        assert me["response"]["mode"] == "max_edge"
        assert sr["response"]["mode"] == "smart_resize"

    def test_duplicate_key_overwrites(self, cache):
        cache.put("001.png", "ape_current", 42, 0.3, "max_edge",
                  {"version": 1}, 100, 50, 1500)
        cache.put("001.png", "ape_current", 42, 0.3, "max_edge",
                  {"version": 2}, 200, 100, 2000)

        result = cache.get("001.png", "ape_current", 42, 0.3, "max_edge")
        assert result["response"]["version"] == 2
        assert result["tokens_in"] == 200

    def test_stats(self, cache):
        stats = cache.stats()
        assert stats["total_entries"] == 0

        cache.put("001.png", "p1", 42, 0.3, "max_edge",
                  SAMPLE_RESPONSE, 100, 50, 1500)
        cache.put("002.png", "p1", 42, 0.3, "max_edge",
                  SAMPLE_RESPONSE, 100, 50, 1500)

        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["size_bytes"] > 0

    def test_db_auto_created(self, tmp_path):
        cache_dir = tmp_path / "new_cache_dir"
        assert not cache_dir.exists()
        cache = ResponseCache(cache_dir)
        assert cache_dir.exists()
        assert (cache_dir / "llm_responses.db").exists()
