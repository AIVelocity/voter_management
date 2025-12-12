from .search_api import voters_search,family_dropdown_search
from .single_voters_api import single_voters_info
from .update_api import update_voter
from .voters_info_api import voters_info
from .add_voter_api import add_voter
from .db_list_api import tags ,index , roles
from .add_relationship_api import add_relation,remove_relation
from .admin_dashboard_api import dashboard,admin_allocation_panel
from .filter_api import filter
from .caste_religion_api import caste_dropdown,religion_dropdown
from .occupation_api import occupation_dropdown
from .registration_api import registration
from .id_validation_api import id_validation

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
    "religion_dropdown",
    "occupation_dropdown",
    "registration",
    "id_validation",
    "admin_allocation_panel"
]