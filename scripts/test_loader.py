#!/usr/bin/env python3
"""Quick test script to verify CUAD data loader works."""

import sys
sys.path.insert(0, ".")

from src.data import CUADDataLoader, CATEGORY_TIERS, get_category_tier


def main():
    print("=" * 60)
    print("Testing CUAD Data Loader")
    print("=" * 60)

    # Initialize loader
    print("\n1. Initializing loader...")
    loader = CUADDataLoader(split="test")

    # Load dataset
    print("2. Loading dataset from local JSON file...")
    loader.load()
    print(f"   ✓ Loaded {len(loader):,} samples")

    # Get stats
    print("\n3. Dataset statistics:")
    stats = loader.stats()
    print(f"   Total Q&A pairs:        {stats['total_samples']:,}")
    print(f"   Positive (has clause):  {stats['positive_samples']:,} ({stats['positive_rate']:.1%})")
    print(f"   Negative (no clause):   {stats['negative_samples']:,}")
    print(f"   Total answer spans:     {stats['total_answer_spans']:,} (the ~13k CUAD labels)")
    print(f"   Avg spans per positive: {stats['avg_spans_per_positive']:.1f}")
    print(f"   Categories:             {stats['num_categories']}")
    print(f"   Contracts:              {stats['num_contracts']}")

    # Show category tiers
    print("\n4. Category tiers:")
    print(f"   Common (easy):    {len(CATEGORY_TIERS['common'])} categories")
    print(f"   Moderate:         {len(CATEGORY_TIERS['moderate'])} categories")
    print(f"   Rare (hard):      {len(CATEGORY_TIERS['rare'])} categories")

    # Sample a few items
    print("\n5. Sample items:")
    for i, sample in enumerate(loader):
        if i >= 3:
            break
        print(f"\n   Sample {i + 1}:")
        print(f"   - ID: {sample.id}")
        print(f"   - Category: {sample.category}")
        print(f"   - Tier: {sample.tier}")
        print(f"   - Contract length: {len(sample.contract_text):,} chars")
        print(f"   - Has ground truth: {'Yes' if sample.ground_truth else 'No'}")
        if sample.ground_truth:
            gt_preview = sample.ground_truth[:100] + "..." if len(sample.ground_truth) > 100 else sample.ground_truth
            print(f"   - Ground truth: {gt_preview}")

    # Test get_by_tier
    print("\n6. Testing tier filtering:")
    rare_samples = loader.get_by_tier("rare")
    print(f"   Rare tier samples: {len(rare_samples)}")

    # Test get_by_category
    print("\n7. Testing category filtering:")
    gov_law = loader.get_by_category("Governing Law")
    print(f"   'Governing Law' samples: {len(gov_law)}")

    print("\n" + "=" * 60)
    print("✓ Data loader test PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
