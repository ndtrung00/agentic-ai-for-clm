"""Tests for agent modules."""

import pytest

from src.agents.base import AgentConfig, ExtractionResult
from src.agents.orchestrator import Orchestrator, CATEGORY_ROUTING
from src.agents.risk_liability import RiskLiabilityAgent, RISK_LIABILITY_CATEGORIES
from src.agents.temporal_renewal import TemporalRenewalAgent, TEMPORAL_RENEWAL_CATEGORIES
from src.agents.ip_commercial import IPCommercialAgent, IP_COMMERCIAL_CATEGORIES


class TestAgentConfig:
    """Tests for agent configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AgentConfig(name="test")
        assert config.name == "test"
        assert config.model_key == "claude-sonnet"
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.categories == []

    def test_custom_config(self):
        """Test custom configuration."""
        config = AgentConfig(
            name="custom",
            model_key="claude-opus-4-20250514",
            temperature=0.5,
            max_tokens=8192,
            categories=["cat1", "cat2"],
        )
        assert config.model_key == "claude-opus-4-20250514"
        assert config.temperature == 0.5
        assert len(config.categories) == 2


class TestExtractionResult:
    """Tests for extraction result structure."""

    def test_empty_result(self):
        """Test empty extraction result."""
        result = ExtractionResult()
        assert result.extracted_clauses == []
        assert result.reasoning == ""
        assert result.confidence == 0.0

    def test_populated_result(self):
        """Test populated extraction result."""
        result = ExtractionResult(
            extracted_clauses=["clause 1", "clause 2"],
            reasoning="Found two relevant clauses",
            confidence=0.85,
            category_indicators_found=["liability", "cap"],
            category="Cap on Liability",
        )
        assert len(result.extracted_clauses) == 2
        assert result.confidence == 0.85


class TestCategoryRouting:
    """Tests for orchestrator category routing."""

    def test_all_categories_routed(self):
        """Test that all 41 categories have routing."""
        all_categories = (
            RISK_LIABILITY_CATEGORIES
            + TEMPORAL_RENEWAL_CATEGORIES
            + IP_COMMERCIAL_CATEGORIES
        )
        for category in all_categories:
            assert category in CATEGORY_ROUTING, f"Missing routing for {category}"

    def test_routing_to_risk_liability(self):
        """Test routing to risk/liability specialist."""
        for category in RISK_LIABILITY_CATEGORIES:
            assert CATEGORY_ROUTING[category] == "risk_liability"

    def test_routing_to_temporal_renewal(self):
        """Test routing to temporal/renewal specialist."""
        for category in TEMPORAL_RENEWAL_CATEGORIES:
            assert CATEGORY_ROUTING[category] == "temporal_renewal"

    def test_routing_to_ip_commercial(self):
        """Test routing to IP/commercial specialist."""
        for category in IP_COMMERCIAL_CATEGORIES:
            assert CATEGORY_ROUTING[category] == "ip_commercial"


class TestRiskLiabilityAgent:
    """Tests for risk/liability specialist."""

    @pytest.fixture
    def agent(self):
        """Create risk/liability agent."""
        return RiskLiabilityAgent()

    def test_agent_creation(self, agent):
        """Test agent can be created."""
        assert agent.name == "risk_liability"
        assert len(agent.config.categories) == 13

    def test_handles_category(self, agent):
        """Test category handling."""
        assert agent.handles_category("Uncapped Liability")
        assert agent.handles_category("Cap on Liability")
        assert not agent.handles_category("Governing Law")

    def test_get_prompt(self, agent):
        """Test prompt generation returns system and user templates."""
        system, user = agent.get_prompt()
        assert "liability" in system.lower()
        assert len(user) > 0


class TestTemporalRenewalAgent:
    """Tests for temporal/renewal specialist."""

    @pytest.fixture
    def agent(self):
        """Create temporal/renewal agent."""
        return TemporalRenewalAgent()

    def test_agent_creation(self, agent):
        """Test agent can be created."""
        assert agent.name == "temporal_renewal"
        assert len(agent.config.categories) == 11

    def test_handles_category(self, agent):
        """Test category handling."""
        assert agent.handles_category("Governing Law")
        assert agent.handles_category("Renewal Term")
        assert not agent.handles_category("Uncapped Liability")


class TestIPCommercialAgent:
    """Tests for IP/commercial specialist."""

    @pytest.fixture
    def agent(self):
        """Create IP/commercial agent."""
        return IPCommercialAgent()

    def test_agent_creation(self, agent):
        """Test agent can be created."""
        assert agent.name == "ip_commercial"
        assert len(agent.config.categories) == 17

    def test_handles_category(self, agent):
        """Test category handling."""
        assert agent.handles_category("License Grant")
        assert agent.handles_category("Non-Compete")
        assert not agent.handles_category("Governing Law")


class TestOrchestrator:
    """Tests for orchestrator agent."""

    def test_route_category_known(self):
        """Test routing known categories."""
        orchestrator = Orchestrator(specialists={})
        assert orchestrator.route_category("Governing Law") == "temporal_renewal"
        assert orchestrator.route_category("Cap on Liability") == "risk_liability"
        assert orchestrator.route_category("License Grant") == "ip_commercial"

    def test_route_category_unknown(self):
        """Test routing unknown category raises error."""
        orchestrator = Orchestrator(specialists={})
        with pytest.raises(ValueError, match="Unknown category"):
            orchestrator.route_category("Nonexistent Category")
