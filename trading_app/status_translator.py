"""
Status Translation Layer - Normalize edge_registry vs edge_candidates statuses

NO SCHEMA CHANGES - Pure translation between old and new vocabularies
"""

# edge_registry → edge_candidates status mapping
LEGACY_TO_CANONICAL = {
    'NEVER_TESTED': 'DRAFT',
    'TESTED_FAILED': 'REJECTED',
    'VALIDATED': 'APPROVED',
    'PROMOTED': 'PROMOTED',
    'RETIRED': 'REJECTED'
}

# edge_candidates → edge_registry status mapping (reverse)
CANONICAL_TO_LEGACY = {v: k for k, v in LEGACY_TO_CANONICAL.items()}


def translate_status_to_canonical(legacy_status: str) -> str:
    """
    Translate edge_registry status → edge_candidates status

    Args:
        legacy_status: Status from edge_registry vocabulary

    Returns:
        Equivalent status in edge_candidates vocabulary
    """
    return LEGACY_TO_CANONICAL.get(legacy_status, legacy_status)


def translate_status_to_legacy(canonical_status: str) -> str:
    """
    Translate edge_candidates status → edge_registry status

    Args:
        canonical_status: Status from edge_candidates vocabulary

    Returns:
        Equivalent status in edge_registry vocabulary
    """
    return CANONICAL_TO_LEGACY.get(canonical_status, canonical_status)


def is_promoted(candidate: dict) -> bool:
    """
    Check if candidate is promoted (canonical way)

    Args:
        candidate: Row from edge_candidates table

    Returns:
        True if promoted to validated_setups
    """
    return candidate.get('promoted_validated_setup_id') is not None
