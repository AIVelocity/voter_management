from ..models import VoterRelationshipDetails

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
    

def get_family_from_db(voter):

    relations = (
        VoterRelationshipDetails.objects
        .filter(voter=voter)
        .select_related("related_voter")
    )

    siblings = []
    children = []

    father_name = mother_name = wife_name = husband_name = None

    for rel in relations:
        p = rel.related_voter

        member = {
            "name": f"{p.first_name} {p.middle_name} {p.last_name}",
            "voter_list_id": p.voter_list_id,
        }

        rel_type = rel.relation_with_voter

        if rel_type == "father":
            father_name = member

        elif rel_type == "mother":
            mother_name = member

        elif rel_type == "wife":
            wife_name = member

        elif rel_type == "husband":
            husband_name = member

        elif rel_type == "child":
            children.append(member)

        elif rel_type == "sibling":
            siblings.append(member)

    return {
        "father": father_name,
        "mother": mother_name,
        "wife": wife_name,
        "husband": husband_name,
        "siblings": siblings,
        "children": children,
    }
