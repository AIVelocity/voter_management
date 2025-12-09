from .search_api import voters_search,family_dropdown_search
from .single_voters_api import single_voters_info
from .update_api import update_voter
from .voters_info_api import voters_info
from .add_voter_api import add_voter
from .db_list_api import tags ,index , roles
from .add_relationship_api import add_relation,remove_relation
from .dashboard_api import dashboard
from .filter_api import filter
from .caste_religion_api import caste_dropdown,religion_dropdown

__all__ = [
    "tags",
    "index",
    "voters_info",
    "single_voters_info",
    "update_voter",
    "add_voter",
    "voters_search",
    "roles",
    "add_relation",
    "remove_relation",
    "family_dropdown_search",
    "dashboard",
    "filter",
    "caste_dropdown",
    "religion_dropdown"
]