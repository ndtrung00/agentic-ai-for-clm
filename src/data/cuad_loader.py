"""CUAD dataset loader.

Supports loading from:
1. Local JSON file (data/cuad/CUAD_v1.json)
2. HuggingFace datasets (theatticusproject/cuad-qa)

Dataset stats:
- Test contracts: 102
- Test data points: 4,128
- Categories: 41 clause types
- Label distribution: 30% positive / 70% negative
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Any
import json


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


# Default local data path
LOCAL_CUAD_PATH = Path(__file__).parent.parent.parent / "data" / "cuad" / "CUAD_v1.json"


@dataclass
class CUADSample:
    """A single CUAD evaluation sample."""

    id: str
    contract_text: str
    category: str
    question: str
    ground_truth: str  # First answer span (empty if no clause)
    ground_truth_spans: list[str]  # All answer spans
    contract_title: str
    tier: str  # 'common', 'moderate', 'rare'

    @property
    def has_clause(self) -> bool:
        """Whether this sample has at least one clause."""
        return len(self.ground_truth_spans) > 0

    @property
    def num_spans(self) -> int:
        """Number of answer spans."""
        return len(self.ground_truth_spans)


class CUADDataLoader:
    """Loader for CUAD dataset.

    Supports loading from local JSON file or HuggingFace.
    """

    def __init__(
        self,
        split: str = "test",
        local_path: Path | str | None = None,
        use_huggingface: bool = False,
    ) -> None:
        """Initialize the CUAD loader.

        Args:
            split: Dataset split to load ('train', 'validation', 'test').
            local_path: Path to local CUAD JSON file. If None, uses default.
            use_huggingface: If True, load from HuggingFace instead of local.
        """
        self.split = split
        self.local_path = Path(local_path) if local_path else LOCAL_CUAD_PATH
        self.use_huggingface = use_huggingface
        self._samples: list[CUADSample] = []
        self._loaded = False

    def load(self) -> None:
        """Load the CUAD dataset."""
        if self.use_huggingface:
            self._load_from_huggingface()
        else:
            self._load_from_local()
        self._loaded = True

    def _load_from_local(self) -> None:
        """Load from local JSON file."""
        if not self.local_path.exists():
            raise FileNotFoundError(
                f"CUAD data not found at {self.local_path}. "
                "Download from https://github.com/TheAtticusProject/cuad or use use_huggingface=True"
            )

        with open(self.local_path) as f:
            data = json.load(f)

        # CUAD JSON format: {"data": [{"paragraphs": [...], "title": "..."}]}
        for doc in data.get("data", []):
            title = doc.get("title", "")
            for para in doc.get("paragraphs", []):
                context = para.get("context", "")
                for qa in para.get("qas", []):
                    question = qa.get("question", "")
                    qa_id = qa.get("id", "")
                    answers = qa.get("answers", [])
                    answer_texts = [a["text"] for a in answers]
                    ground_truth = answer_texts[0] if answer_texts else ""

                    category = self._extract_category(question, qa_id)
                    sample = CUADSample(
                        id=qa_id,
                        contract_text=context,
                        category=category,
                        question=question,
                        ground_truth=ground_truth,
                        ground_truth_spans=answer_texts,
                        contract_title=title,
                        tier=get_category_tier(category),
                    )
                    self._samples.append(sample)

    def _load_from_huggingface(self) -> None:
        """Load from HuggingFace datasets."""
        try:
            from datasets import load_dataset
        except ImportError as e:
            raise ImportError(
                "HuggingFace datasets not available. Install with: pip install datasets"
            ) from e

        dataset = load_dataset("theatticusproject/cuad-qa", split=self.split)

        for item in dataset:
            sample = self._parse_hf_item(item)
            self._samples.append(sample)

    def _parse_hf_item(self, item: dict[str, Any]) -> CUADSample:
        """Parse HuggingFace dataset item."""
        question = item["question"]
        category = self._extract_category(question)
        answers = item.get("answers", {})
        answer_texts = answers.get("text", [])
        ground_truth = answer_texts[0] if answer_texts else ""

        return CUADSample(
            id=item["id"],
            contract_text=item["context"],
            category=category,
            question=question,
            ground_truth=ground_truth,
            ground_truth_spans=answer_texts,
            contract_title=item.get("title", ""),
            tier=get_category_tier(category),
        )

    def __len__(self) -> int:
        """Get the number of samples in the dataset."""
        if not self._loaded:
            raise RuntimeError("Dataset not loaded. Call load() first.")
        return len(self._samples)

    def __iter__(self) -> Iterator[CUADSample]:
        """Iterate over CUAD samples."""
        if not self._loaded:
            raise RuntimeError("Dataset not loaded. Call load() first.")
        yield from self._samples

    def _extract_category(self, question: str, qa_id: str = "") -> str:
        """Extract category name from CUAD question or ID.

        Args:
            question: The CUAD question text.
            qa_id: The question ID (format: CONTRACT__Category Name)

        Returns:
            Category name.
        """
        # Try extracting from ID first (most reliable)
        # Format: "CONTRACT_NAME__Category Name"
        if qa_id and "__" in qa_id:
            category = qa_id.split("__")[-1]
            return category

        # Try double quotes (local CUAD format)
        # "Highlight the parts (if any) of this contract related to "Document Name""
        if '"' in question:
            import re
            match = re.search(r'"([^"]+)"', question)
            if match:
                return match.group(1)

        # Try single quotes (HuggingFace format)
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
        return [s for s in self._samples if s.category == category]

    def get_by_tier(self, tier: str) -> list[CUADSample]:
        """Get all samples for a difficulty tier.

        Args:
            tier: 'common', 'moderate', or 'rare'.

        Returns:
            List of samples in that tier.
        """
        return [s for s in self._samples if s.tier == tier]

    def get_categories(self) -> list[str]:
        """Get all unique categories in the dataset.

        Returns:
            List of category names.
        """
        return list(set(s.category for s in self._samples))

    def get_contracts(self) -> list[str]:
        """Get all unique contract titles.

        Returns:
            List of contract titles.
        """
        return list(set(s.contract_title for s in self._samples))

    def stats(self) -> dict[str, int | float]:
        """Get dataset statistics.

        Returns:
            Dict with dataset statistics.
        """
        if not self._loaded:
            raise RuntimeError("Dataset not loaded. Call load() first.")

        positive = sum(1 for s in self._samples if s.has_clause)
        negative = len(self._samples) - positive
        total_spans = sum(s.num_spans for s in self._samples)

        return {
            "total_samples": len(self._samples),
            "positive_samples": positive,
            "negative_samples": negative,
            "positive_rate": positive / len(self._samples) if self._samples else 0,
            "total_answer_spans": total_spans,  # The ~13,000 CUAD labels
            "avg_spans_per_positive": total_spans / positive if positive else 0,
            "num_categories": len(self.get_categories()),
            "num_contracts": len(self.get_contracts()),
            "common_tier_samples": len(self.get_by_tier("common")),
            "moderate_tier_samples": len(self.get_by_tier("moderate")),
            "rare_tier_samples": len(self.get_by_tier("rare")),
        }
