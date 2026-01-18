"""Tests for CUAD data loader."""

import pytest

from src.data.cuad_loader import (
    CUADDataLoader,
    CUADSample,
    CATEGORY_TIERS,
    get_category_tier,
)


class TestCategoryTiers:
    """Tests for category tier classification."""

    def test_common_tier(self):
        """Test that common categories are classified correctly."""
        assert get_category_tier("Governing Law") == "common"
        assert get_category_tier("Parties") == "common"
        assert get_category_tier("Agreement Date") == "common"

    def test_moderate_tier(self):
        """Test that moderate categories are classified correctly."""
        assert get_category_tier("Renewal Term") == "moderate"
        assert get_category_tier("License Grant") == "moderate"
        assert get_category_tier("Non-Compete") == "moderate"

    def test_rare_tier(self):
        """Test that rare categories are classified correctly."""
        assert get_category_tier("Uncapped Liability") == "rare"
        assert get_category_tier("Joint Ip Ownership") == "rare"
        assert get_category_tier("Volume Restriction") == "rare"

    def test_unknown_tier(self):
        """Test unknown category returns 'unknown'."""
        assert get_category_tier("NonExistent Category") == "unknown"

    def test_all_categories_classified(self):
        """Test that all tier categories sum correctly."""
        total = sum(len(cats) for cats in CATEGORY_TIERS.values())
        # Should be 41 total categories
        assert total == 41


class TestCUADSample:
    """Tests for CUADSample dataclass."""

    def test_sample_creation(self):
        """Test creating a CUAD sample."""
        sample = CUADSample(
            id="test_001",
            contract_text="This is a test contract.",
            category="Governing Law",
            question="What is the governing law?",
            ground_truth="New York law",
            contract_title="Test Agreement",
            tier="common",
        )
        assert sample.id == "test_001"
        assert sample.tier == "common"

    def test_sample_empty_ground_truth(self):
        """Test sample with no ground truth (negative example)."""
        sample = CUADSample(
            id="test_002",
            contract_text="This contract has no relevant clause.",
            category="Uncapped Liability",
            question="Is there uncapped liability?",
            ground_truth="",
            contract_title="Test Agreement",
            tier="rare",
        )
        assert sample.ground_truth == ""


class TestCUADDataLoader:
    """Tests for CUAD data loader.

    Note: These tests require network access to HuggingFace.
    Mark as slow/integration tests in CI.
    """

    @pytest.fixture
    def loader(self):
        """Create a data loader (not loaded yet)."""
        return CUADDataLoader(split="test")

    def test_loader_creation(self, loader):
        """Test loader can be created."""
        assert loader.split == "test"

    def test_loader_not_loaded_error(self, loader):
        """Test error when accessing dataset before loading."""
        with pytest.raises(RuntimeError, match="not loaded"):
            _ = loader.dataset

    @pytest.mark.slow
    def test_loader_load(self, loader):
        """Test loading the dataset (requires network)."""
        loader.load()
        assert len(loader) > 0

    @pytest.mark.slow
    def test_loader_stats(self, loader):
        """Test dataset statistics (requires network)."""
        loader.load()
        stats = loader.stats()
        assert "total_samples" in stats
        assert "positive_rate" in stats
        assert stats["total_samples"] > 0

    @pytest.mark.slow
    def test_loader_iteration(self, loader):
        """Test iterating over samples (requires network)."""
        loader.load()
        sample = next(iter(loader))
        assert isinstance(sample, CUADSample)
        assert sample.id
        assert sample.category
