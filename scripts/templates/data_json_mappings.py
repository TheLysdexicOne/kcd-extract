# Attribute mappings for each item_type
item_stats_mapping = {
    "default": ["Id"],  # Shared attributes for all item_types
    "MeleeWeapon": ["Id", "Name", "attack", "defense", "weight", "price"],
    "MissileWeapon": ["Id", "Name", "power", "limb_resistance", "weight", "price"],
    "Armor": ["Id", "Name", "defense_stab", "defense_slash", "defense_smash", "weight", "price"],
    "Hood": ["Id", "Name", "defense_stab", "defense_slash", "defense_smash", "weight", "price"],  # Treat Hood as Armor
    "Die": ["Id", "Name", "material"],
    "DiceBadge": ["Id", "Name", "badge_type", "badge_subtype"]
}

item_attr_mapping = ["Id", "Name", "IconId", "UIInfo"]