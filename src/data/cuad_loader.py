"""CUAD dataset loader using HuggingFace datasets.

Dataset: theatticusproject/cuad-qa
- Test contracts: 102
- Test data points: 4,128
- Categories: 41 clause types
- Label distribution: 30% positive / 70% negative
"""

from dataclasses import dataclass
from typing import Iterator

from datasets import load_dataset, Dataset


# Category stratification by ContractEval F1 performance
CATEGORY_TIERS: dict[str, list[str]] = {
    "common": [
        # F1 > 0.7 - Models perform well
        "Governing Law",
        "Parties",
        "Agreement Date",
        "Effective Date",
        "Expiration Date",
        "Document Name",
    ],
    "moderate": [
        # F1 0.3-0.7 - Moderate difficulty
        "Renewal Term",
        "License Grant",
        "Termination For Convenience",
        "Anti-Assignment",
        "Change Of Control",
        "Cap On Liability",
        "Insurance",
        "Audit Rights",
        "Non-Compete",
        "Exclusivity",
        "Non-Transferable License",
        "Irrevocable Or Perpetual License",
        "Rofr/Rofo/Rofn",
        "No-Solicit Of Employees",
        "No-Solicit Of Customers",
        "Ip Ownership Assignment",
        "Warranty Duration",
        "Post-Termination Services",
    ],
    "rare": [
        # F1 near zero - Hardest categories
        "Uncapped Liability",
        "Joint Ip Ownership",
        "Notice Period To Terminate Renewal",
        "Volume Restriction",
        "Minimum Commitment",
        "Revenue/Profit Sharing",
        "Price Restrictions",
        "Most Favored Nation",
        "Competitive Restriction Exception",
        "Third Party Beneficiary",
        "Affiliate License-Licensor",
        "Affiliate License-Licensee",
        "Unlimited/All-You-Can-Eat-License",
        "Source Code Escrow",
        "Liquidated Damages",
        "Covenant Not To Sue",
        "Non-Disparagement",
    ],
}


def get_category_tier(category: str) -> str:
    """Get the difficulty tier for a category.

    Args:
        category: CUAD category name.

    Returns:
        Tier name: 'common', 'moderate', or 'rare'.
    """
    for tier, categories in CATEGORY_TIERS.items():
        if category in categories:
            return tier
    return "unknown"


@dataclass
class CUADSample:
    """A single CUAD evaluation sample."""

    id: str
    contract_text: str
    category: str
    question: str
    ground_truth: str  # Empty string if no clause
    contract_title: str
    tier: str  # 'common', 'moderate', 'rare'


class CUADDataLoader:
    """Loader for CUAD dataset from HuggingFace."""

    def __init__(self, split: str = "test") -> None:
        """Initialize the CUAD loader.

        Args:
            split: Dataset split to load ('train', 'validation', 'test').
        """
        self.split = split
        self._dataset: Dataset | None = None

    def load(self) -> None:
        """Load the CUAD dataset from HuggingFace."""
        self._dataset = load_dataset(
            "theatticusproject/cuad-qa",
            split=self.split,
        )

    @property
    def dataset(self) -> Dataset:
        """Get the loaded dataset.

        Returns:
            The HuggingFace Dataset object.

        Raises:
            RuntimeError: If dataset not loaded.
        """
        if self._dataset is None:
            raise RuntimeError("Dataset not loaded. Call load() first.")
        return self._dataset

    def __len__(self) -> int:
        """Get the number of samples in the dataset."""
        return len(self.dataset)

    def __iter__(self) -> Iterator[CUADSample]:
        """Iterate over CUAD samples."""
        for item in self.dataset:
            yield self._parse_item(item)

    def _parse_item(self, item: dict) -> CUADSample:
        """Parse a raw dataset item into CUADSample.

        Args:
            item: Raw item from HuggingFace dataset.

        Returns:
            Parsed CUADSample.
        """
        # Extract category from question
        # CUAD questions follow pattern: "Highlight the parts..."
        question = item["question"]
        category = self._extract_category(question)

        # Get answers (may be empty list)
        answers = item.get("answers", {})
        answer_texts = answers.get("text", [])
        ground_truth = answer_texts[0] if answer_texts else ""

        return CUADSample(
            id=item["id"],
            contract_text=item["context"],
            category=category,
            question=question,
            ground_truth=ground_truth,
            contract_title=item.get("title", ""),
            tier=get_category_tier(category),
        )

    def _extract_category(self, question: str) -> str:
        """Extract category name from CUAD question.

        Args:
            question: The CUAD question text.

        Returns:
            Category name.
        """
        # CUAD questions follow patterns like:
        # "Highlight the parts (if any) of this contract related to 'Governing Law'"
        # We need to extract the category name from quotes
        if "'" in question:
            start = question.find("'") + 1
            end = question.find("'", start)
            if end > start:
                return question[start:end]

        # Fallback: return full question
        return question

    def get_by_category(self, category: str) -> list[CUADSample]:
        """Get all samples for a specific category.

        Args:
            category: The CUAD category name.

        Returns:
            List of samples for that category.
        """
        return [s for s in self if s.category == category]

    def get_by_tier(self, tier: str) -> list[CUADSample]:
        """Get all samples for a difficulty tier.

        Args:
            tier: 'common', 'moderate', or 'rare'.

        Returns:
            List of samples in that tier.
        """
        return [s for s in self if s.tier == tier]

    def get_categories(self) -> list[str]:
        """Get all unique categories in the dataset.

        Returns:
            List of category names.
        """
        return list(set(s.category for s in self))

    def get_contracts(self) -> list[str]:
        """Get all unique contract titles.

        Returns:
            List of contract titles.
        """
        return list(set(s.contract_title for s in self))

    def stats(self) -> dict[str, int | float]:
        """Get dataset statistics.

        Returns:
            Dict with dataset statistics.
        """
        samples = list(self)
        positive = sum(1 for s in samples if s.ground_truth)
        negative = len(samples) - positive

        return {
            "total_samples": len(samples),
            "positive_samples": positive,
            "negative_samples": negative,
            "positive_rate": positive / len(samples) if samples else 0,
            "num_categories": len(self.get_categories()),
            "num_contracts": len(self.get_contracts()),
            "common_tier_samples": len(self.get_by_tier("common")),
            "moderate_tier_samples": len(self.get_by_tier("moderate")),
            "rare_tier_samples": len(self.get_by_tier("rare")),
        }
