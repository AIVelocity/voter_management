from django.http import JsonResponse
from ..models import VoterList,VoterTag
from .view_utils import save_relation,get_family_from_db

# single voter info
def single_voters_info(request, voter_list_id):

    try:
        voter = VoterList.objects.select_related("tag_id").get(
            voter_list_id=voter_list_id
        )
    except VoterList.DoesNotExist:
        return JsonResponse({
            "status": False,
            "message": "Voter not found"
        }, status=404)


    # ---------------- HELPERS ----------------

    def safe_age(v):
        val = str(v or "").lower().strip()
        try:
            return int(val, 16) if val.startswith("0x") else int(val)
        except:
            return None

    def parse_kramank(value):
        try:
            return int(str(value).split("/")[-1])
        except:
            return 0

    # ---------------- COMPUTE ----------------

    age = safe_age(voter.age_eng)
    kramank = parse_kramank(voter.kramank)

    # full_address = (voter.address_line1 or "") + \
    #           (voter.address_line2 or "") + \
    #           (voter.address_line3 or "")

    # ---------------- FATHER ----------------
    def calculate_and_save_family(voter):
        is_male = voter.gender_eng.lower() == "male"

        father = father_name = father_id = None
        mother = mother_name = mother_id = None
        wife = wife_name = wife_id = None
        husband = husband_name = husband_id = None

        siblings = []
        children = []
        other_relatives = []
        BloodRelatedFam = []

        # -------- YOUR EXISTING LOGIC -----------
        # (No behavioural change)

        # --- MALE ---
        if is_male:
            father = VoterList.objects.filter(
                first_name=voter.middle_name,
                last_name=voter.last_name,
                gender_eng__iexact="male"
            ).first()

            if father:
                father_name = f"{father.first_name} {father.middle_name} {father.last_name}"
                father_id = father.voter_list_id
            else:
                father_name = " ".join(filter(None, [
                    voter.middle_name,
                    voter.last_name
                ]))

        # --- FEMALE ---
        else:
            male_match = VoterList.objects.filter(
                first_name=voter.middle_name,
                last_name=voter.last_name,
                gender_eng__iexact="male"
            ).first()

            voter_age = safe_age(voter.age_eng)
            male_age = safe_age(male_match.age_eng) if male_match else None

            if male_match and voter_age and male_age:
                age_gap = male_age - voter_age

                if age_gap >= 18:
                    father = male_match
                    father_name = f"{father.first_name} {father.middle_name} {father.last_name}"
                    father_id = father.voter_list_id
                else:
                    husband = male_match
                    husband_name = f"{husband.first_name} {husband.middle_name} {husband.last_name}"
                    husband_id = husband.voter_list_id

        # --- MOTHER ---
        if father:
            mother = VoterList.objects.filter(
                middle_name=father.first_name,
                last_name=father.last_name,
                gender_eng__iexact="female"
            ).first()

            if mother:
                mother_name = f"{mother.first_name} {mother.middle_name} {mother.last_name}"
                mother_id = mother.voter_list_id

        # ---- SIBLINGS ----

        father_first_name_for_siblings = (
            father.first_name if is_male and father else voter.middle_name
        )

        if father_first_name_for_siblings and age and kramank:
            family_members = VoterList.objects.filter(
                last_name=voter.last_name
            ).exclude(voter_list_id=voter.voter_list_id)

            for p in family_members:
                p_age = safe_age(p.age_eng)
                p_kramank = parse_kramank(p.kramank)

                if (
                    p.middle_name == father_first_name_for_siblings and
                    p_age is not None and
                    age is not None and
                    abs(p_age - age) <= 18 and
                    p_kramank and
                    abs(p_kramank - kramank) <= 5
                ):
                    siblings.append({
                        "name": f"{p.first_name} {p.middle_name} {p.last_name}",
                        "voter_list_id": p.voter_list_id
                    })

        # ---- WIFE ----
        if is_male:
            wife = VoterList.objects.filter(
                middle_name=voter.first_name,
                last_name=voter.last_name,
                gender_eng__iexact="female"
            ).first()

            if wife:
                wife_name = f"{wife.first_name} {wife.middle_name} {wife.last_name}"
                wife_id = wife.voter_list_id

        # ---- CHILDREN ----

        parent_firstname_for_child = (
            voter.first_name if is_male
            else husband.first_name if husband
            else None
        )

        if parent_firstname_for_child and age and kramank:
            kids = VoterList.objects.filter(
                middle_name=parent_firstname_for_child,
                last_name=voter.last_name
            ).exclude(voter_list_id=voter.voter_list_id)

            for kid in kids:
                kid_age = safe_age(kid.age_eng)
                kid_kramank = parse_kramank(kid.kramank)

                if kid_age and age - kid_age >= 15 and abs(kid_kramank - kramank) <= 5:
                    children.append({
                        "name": f"{kid.first_name} {kid.middle_name} {kid.last_name}",
                        "voter_list_id": kid.voter_list_id
                    })

        # ---- REMOVE SIBLINGS DUPED AS CHILDREN ----

        child_ids = {c["voter_list_id"] for c in children}
        siblings = [s for s in siblings if s["voter_list_id"] not in child_ids]

        # ---- SAVE RELATIONSHIPS ----

        save_relation(voter, "father", father_id)
        save_relation(voter, "mother", mother_id)
        save_relation(voter, "husband", husband_id)
        save_relation(voter, "wife", wife_id)

        for c in children:
            save_relation(voter, "child", c["voter_list_id"])

        for s in siblings:
            save_relation(voter, "sibling", s["voter_list_id"])

        # ---- BUILD RESPONSE OBJECT ----

        BloodRelatedFam.extend(
            [
                {"relation": "Father",  "name": father_name,  "voter_list_id": father_id},
                {"relation": "Mother",  "name": mother_name,  "voter_list_id": mother_id},
                {"relation": "Wife",    "name": wife_name,    "voter_list_id": wife_id},
                {"relation": "Husband","name": husband_name, "voter_list_id": husband_id},
            ]
        )

        BloodRelatedFam += [
            {"relation": "Child","name": c["name"],"voter_list_id": c["voter_list_id"]}
            for c in children
        ]

        BloodRelatedFam += [
            {"relation": "Sibling","name": s["name"],"voter_list_id": s["voter_list_id"]}
            for s in siblings
        ]

        return {
            "father_name": father_name,
            "mother_name": mother_name,
            "wife_name": wife_name,
            "husband_name": husband_name,
            "siblings": siblings,
            "children": children,
            "BloodRelatedFam": BloodRelatedFam
        }

    # first try DB
    family = get_family_from_db(voter)

    # if empty → calculate & persist → re-fetch from DB
    # if not (
    #     family["father"] or family["mother"] or family["wife"]
    #     or family["husband"] or family["siblings"] or family["children"]
    # ):
    #     calculate_and_save_family(voter)
        # family = get_family_from_db(voter)

    BloodRelatedFam = []

    if family["father"]:
        BloodRelatedFam.append({
            "relation": "Father",
            "name": family["father"]["name"],
            "voter_list_id": family["father"]["voter_list_id"],
        })

    if family["mother"]:
        BloodRelatedFam.append({
            "relation": "Mother",
            "name": family["mother"]["name"],
            "voter_list_id": family["mother"]["voter_list_id"],
        })

    if family["husband"]:
        BloodRelatedFam.append({
            "relation": "Husband",
            "name": family["husband"]["name"],
            "voter_list_id": family["husband"]["voter_list_id"],
        })

    spouse = None

    if family["wife"]:
        spouse = {
            "name": family["wife"]["name"],
            "voter_list_id": family["wife"]["voter_list_id"]
        }

    elif family["husband"]:
        spouse = {
            "name": family["husband"]["name"],
            "voter_list_id": family["husband"]["voter_list_id"]
        }

    if spouse:
        BloodRelatedFam.append({
            "relation": "Spouse",
            "name": spouse["name"],
            "voter_list_id": spouse["voter_list_id"],
        })


    for s in family["siblings"]:
        BloodRelatedFam.append({
            "relation": "Sibling",
            "name": s["name"],
            "voter_list_id": s["voter_list_id"],
        })

    data = {
        "voter_list_id": voter.voter_list_id,
        "voter_name_eng": voter.voter_name_eng,
        "sr_no": voter.sr_no,
        "voter_id": voter.voter_id,
        
        "first_name": voter.first_name,
        "middle_name": voter.middle_name,
        "last_name": voter.last_name,

        "kramank": voter.kramank,
        "address": voter.current_address,
        "full_address": voter.address_line1,

        "mobile_no": voter.mobile_no,
        "alternate_mobile_no1": voter.alternate_mobile1,
        "alternate_mobile_no2": voter.alternate_mobile2,

        "age": age,
        "gender": voter.gender_eng,
        
        "ward_id": voter.ward_no,
        
        "tag": voter.tag_id.tag_name if voter.tag_id else None,
        "tag_obj" : {
            "name" : voter.tag_id.tag_name if voter.tag_id else None,
            "id" :voter.tag_id.tag_id if voter.tag_id else None
                },
        
        "occupation":voter.occupation,
        "cast":voter.cast,
        "organisation":voter.organisation,
        "comments" : voter.comments,
        
        "badge":voter.badge,
        "location":voter.location,
        "BloodRelatedFam": BloodRelatedFam,
        "father": family["father"],
        "mother": family["mother"],
        "spouse" : spouse,
        # "wife": family["wife"],
        # "husband": family["husband"],
        "siblings": family["siblings"],
        "children": family["children"], 

    }

    return JsonResponse({"status": True, "data": data})
