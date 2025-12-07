from django.http import JsonResponse
from ..models import VoterList,VoterTag


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

    address = (voter.address_line1 or "") + \
              (voter.address_line2 or "") + \
              (voter.address_line3 or "")

    # ---------------- FATHER ----------------
    is_male = voter.gender_eng.lower() == "male"
    
    # =====================================================
    # MALE VOTER  ---> FIND FATHER 
    # =====================================================
    
    father = None
    father_name = None
    father_id = None
    husband = None
    husband_name = None
    husband_id = None
    BloodRelatedFam = []
    
    # ---------------- MALE VOTER ----------------
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
            
    
    # ---------------- FEMALE VOTER ----------------
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
    
            #  FATHER CASE
            if age_gap >= 18:
                father = male_match
                father_name = f"{father.first_name} {father.middle_name} {father.last_name}"
                father_id = father.voter_list_id
    
            #  HUSBAND CASE
            else:
                husband = male_match
                husband_name = f"{husband.first_name} {husband.middle_name} {husband.last_name}"
                husband_id = husband.voter_list_id

    # ---------------- MOTHER ----------------
    
    mother = None
    mother_name = None
    mother_id = None
    
    if father :
        mother = VoterList.objects.filter(
            middle_name=father.first_name,
            last_name=father.last_name,
            gender_eng__iexact="female"
        ).first()
    
        if mother:
            mother_name = f"{mother.first_name} {mother.middle_name} {mother.last_name}"
            mother_id = mother.voter_list_id

    # ---------------- SIBLINGS + RELATIVES ----------------

    siblings = []
    other_relatives = []

    # Determine father-name source for siblings
    father_first_name_for_siblings = None

    if is_male and father:
        father_first_name_for_siblings = father.first_name

    elif not is_male:
        father_first_name_for_siblings = voter.middle_name   # female → maiden father name


    if father_first_name_for_siblings and age and kramank:

        family_members = VoterList.objects.filter(
            last_name=voter.last_name
        ).exclude(voter_list_id=voter.voter_list_id)

        voter_age = age
        voter_kramank = kramank

        for p in family_members:

            p_age = safe_age(p.age_eng)
            p_kramank = parse_kramank(p.kramank)

            member = {
                "name": f"{p.first_name} {p.middle_name} {p.last_name}",
                "voter_list_id" : p.voter_list_id
            }

            #  FINAL SIBLING CHECK
            if (
                p.middle_name == father_first_name_for_siblings and
                p_age is not None and
                voter_age is not None and
                abs(p_age - voter_age) <= 18 and
                p_kramank and
                abs(p_kramank - voter_kramank) <= 5
            ):
                siblings.append(member)

            else:
                other_relatives.append(member)

    # ---------------- WIFE ----------------

    wife = None
    wife_name = None
    wife_id = None

    if is_male:
        wife = VoterList.objects.filter(
            middle_name=voter.first_name,
            last_name=voter.last_name,
            gender_eng__iexact="female"
        ).first()

        if wife:
            wife_name = f"{wife.first_name} {wife.middle_name} {wife.last_name}"
            wife_id = wife.voter_list_id

    # ---------------- CHILDREN ----------------

    children = []

    parent_age = age
    parent_kramank = kramank 
    # Determine which name should match child's middle_name
    parent_firstname_for_child = None

    if is_male:
        parent_firstname_for_child = voter.first_name

    elif not is_male and husband:
        parent_firstname_for_child = husband.first_name

    if parent_firstname_for_child and parent_age and parent_kramank:

        kids = VoterList.objects.filter(
            middle_name=parent_firstname_for_child,
            last_name=voter.last_name
        ).exclude(voter_list_id=voter.voter_list_id)

        for kid in kids:

            kid_age = safe_age(kid.age_eng)
            kid_kramank = parse_kramank(kid.kramank)

            #  FINAL VALID CHILD CHECK
            if (
                kid_age is not None
                and parent_age - kid_age >= 15
                and abs(kid_kramank - parent_kramank) <= 5   # KEY FIX
            ):
                children.append({
                    "name": f"{kid.first_name} {kid.middle_name} {kid.last_name}",
                    # "age": kid_age,
                    # "gender": kid.gender_eng,
                    "voter_list_id": kid.voter_list_id,
                })

    # ---------------- REMOVE SIBLINGS WHO ARE CHILDREN ----------------

    child_names = {child["name"] for child in children}

    siblings = [
        sib for sib in siblings
        if sib["name"] not in child_names
    ]
    BloodRelatedFam = []

    BloodRelatedFam.extend(
        ([{"relation": "Father", "name": father_name, "voter_list_id": father_id}]
            if father_name else [{"relation": "Father", "name": "", "voter_list_id": None}]) +
    
        ([{"relation": "Mother", "name": mother_name, "voter_list_id": mother_id}]
            if mother_name else [{"relation": "Mother", "name": "", "voter_list_id": None}]) +
    
        ([{"relation": "Wife", "name": wife_name, "voter_list_id": wife_id}]
            if wife_name else [{"relation": "Wife", "name": "", "voter_list_id": None}]) +
    
        ([{"relation": "Husband", "name": husband_name, "voter_list_id": husband_id}]
            if husband_name else [{"relation": "Husband", "name": "", "voter_list_id": None}]) +
    
        (
            [{"relation": "Child", "name": c["name"], "voter_list_id": c.get("voter_list_id")} for c in children]
        ) +
    
        ([
            {
                "relation": (
                    "Brother" if s.get("gender","").lower() == "male"
                    else "Sister" if s.get("gender","").lower() == "female"
                    else "Sibling"
                ),
                "name": s["name"],
                "voter_list_id": s.get("voter_list_id")
            }
            for s in siblings
        ])
    )

    data = {
        "voter_list_id": voter.voter_list_id,
        "voter_name_eng": voter.voter_name_eng,
        "sr_no": voter.sr_no,
        "voter_id": voter.voter_id,
        
        "first_name": voter.first_name,
        "middle_name": voter.middle_name,
        "last_name": voter.last_name,

        "kramank": voter.kramank,
        "address": address,

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
        
        "badge":voter.badge,
        "location":voter.location,
        "BloodRelatedFam": BloodRelatedFam,
        
        "father_name": father_name,
        "mother_name": mother_name,
        "wife_name":wife_name,
        "husband_name": husband_name,
        "siblings": siblings,
        "children": children
        # "other_family_members": other_relatives,

        # "other_family_members": other_relatives
    }

    return JsonResponse({"status": True, "data": data})
