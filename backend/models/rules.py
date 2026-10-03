"""Business and consistency rules for classification and routing."""

from typing import Optional, Tuple
from backend.core.constants import Category, Team, CATEGORY_TO_TEAM


def get_team_for_category(category: Category) -> Team:
    """Return the designated team for a given primary category."""
    team_val = CATEGORY_TO_TEAM.get(category.value, Team.FRONT_LINE_SUPPORT.value)
    return Team(team_val)


def enforce_consistency_rules(
    category: Category,
    secondary_category: Optional[Category],
    is_urgent: bool
) -> Tuple[Category, Optional[Category], Team, bool]:
    """Enforce strict competition consistency rules:

    1. team must match the fixed category-to-team table.
    2. secondary_category must differ from category (null if identical).
    3. if category is spam_irrelevant:
       - is_urgent MUST be false
       - secondary_category MUST be null
    """
    # Rule 1: Get correct team
    team = get_team_for_category(category)

    # Rule 2: Secondary category must differ
    if secondary_category is not None and secondary_category == category:
        secondary_category = None

    # Rule 3: Spam rules
    if category == Category.SPAM_IRRELEVANT:
        is_urgent = False
        secondary_category = None

    return category, secondary_category, team, is_urgent
