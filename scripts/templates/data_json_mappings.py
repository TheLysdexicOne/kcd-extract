# Attribute mappings for each item_type
item_attr_mapping = {
    "default": ["Id", "Name", "IconId", "UIInfo", "UIName"],  # Shared attributes for all item types
    "MeleeWeapon": ["Class", "Skill", "EquipSlot"],
    "MissileWeapon": ["Class", "Skill", "EquipSlot", "AmmoClass"],
    "Armor": ["DefenseClass", "EquipSlot", "Clothing"],
    "Hood": ["DefenseClass", "EquipSlot", "Clothing"],  # Treat Hood as Armor
    "Helmet": ["DefenseClass", "EquipSlot", "Clothing"],  # Treat Helmet as Armor
    "Die": ["Material", "Weight", "SideWeights", "SideValues"],
    "DiceBadge": ["Type", "SubType"]
}

# Attribute transformations
attr_transform = {
    "Type": (["Class"], lambda attrs, data: int(attrs["Class"])), # Rename "Class" to "Type" and integer
    "Type": (["Type"], lambda attrs, data: int(attrs["Type"])), # Type to integer
    "SubType": (["SubType"], lambda attrs, data: int(attrs["SubType"])) # Subtype to Integer
}

# Stat mappings for each item_type
item_stats_mapping = {
    "default": ["Weight", "Price", "MaxQuality", "MaxStatus", "StrReq", "AgiReq", "Charisma", "Conspicuousness", "Noise", "Visibility"],  # Shared attributes for all item_types
    "MeleeWeapon": ["Attack", "AttackModStab", "AttackModSlash", "AttackModSmash", "Defense"],
    "MissileWeapon": ["Power", "Defense"],
    "Armor": ["DefenseStab", "DefenseSlash", "DefenseSmash"],
    "Hood": ["DefenseStab", "DefenseSlash", "DefenseSmash"],  # Treat Hood as Armor
    "Helmet": ["VisorTypeId", "DefenseStab", "DefenseSlash", "DefenseSmash"],  # Treat Helmet as Armor
    #"Die": ["Model"],
    "DiceBadge": ["badge_type", "badge_subtype"]
}

# Stat transformations
stat_transform = {
    "Price": (["Price"], lambda attrs, data: round(attrs["Price"] * 0.1)),
    "AttackStab": (["Attack", "AttackModStab"], lambda attrs, data: round(float(attrs["Attack"]) * float(attrs["AttackModStab"]))),
    "AttackSlash": (["Attack", "AttackModSlash"], lambda attrs, data: round(float(attrs["Attack"]) * float(attrs["AttackModSlash"]))),
    "AttackSmash": (["Attack", "AttackModSmash"], lambda attrs, data: round(float(attrs["Attack"]) * float(attrs["AttackModSmash"]))),
    "Noise": (["Noise"], lambda attrs, data: round(float(attrs["Noise"]) * 100)),
    "Conspicuousness": (["Conspicuousness"], lambda attrs, data: round(50 + (float(attrs["Conspicuousness"]) * 50))),
    "Visibility": (["Visibility"], lambda attrs, data: round(50 + (float(attrs["Visibility"]) * 50)))

}

