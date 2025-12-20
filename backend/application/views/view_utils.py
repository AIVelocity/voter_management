from ..models import VoterRelationshipDetails,ActivityLog
from deep_translator import GoogleTranslator

class Translator:
    def __init__(self, source="auto"):
        self.source = source

    def translate(self, text, target_lang):
        return GoogleTranslator(
            source=self.source,
            target=target_lang
        ).translate(text)


def log_user_update(user, action, description, changed_fields, ip,voter_list_id):
    """
    changed_fields = {
        "mobile_no": {"old": "1111111111", "new": "9999999999"},
        "address_line1": {"old": "Old Address", "new": "New Address"}
    }
    """
    if not changed_fields:
        return  # No changes → no logs

    ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        old_data={k: v["old"] for k, v in changed_fields.items()},
        new_data={k: v["new"] for k, v in changed_fields.items()},
        ip_address=ip,
        voter_id=voter_list_id

    )



def save_relation(voter, relation, related_voter_id):
    """
    Persists a voter relationship safely.
    Prevents duplicates automatically using DB unique constraint.
    """

    if not voter or not related_voter_id:
        return

    VoterRelationshipDetails.objects.get_or_create(
        voter=voter,
        related_voter_id=related_voter_id,
        relation_with_voter=relation.lower(),
    )
    
def build_member(p, is_marathi):
    if is_marathi and p.voter_name_marathi:
        return {
            "name": p.voter_name_marathi,
            "voter_list_id": p.voter_list_id,
        }

    # fallback to English
    return {
        "name": p.voter_name_eng,
        "voter_list_id": p.voter_list_id,
    }
def get_family_from_db(voter, is_marathi=False):

    relations = (
        VoterRelationshipDetails.objects
        .filter(voter=voter)
        .select_related("related_voter")
    )

    siblings = []
    children = []

    father = mother = spouse = wife = husband = None

    for rel in relations:
        p = rel.related_voter
        member = build_member(p, is_marathi)

        rel_type = rel.relation_with_voter

        if rel_type == "father":
            father = member

        elif rel_type == "mother":
            mother = member

        elif rel_type == "spouse":
            spouse = member

        elif rel_type == "wife":
            wife = member

        elif rel_type == "husband":
            husband = member

        elif rel_type == "child":
            children.append(member)

        elif rel_type == "sibling":
            siblings.append(member)

    return {
        "father": father,
        "mother": mother,
        "wife": wife,
        "husband": husband,
        "spouse": spouse,
        "siblings": siblings,
        "children": children,
    }
