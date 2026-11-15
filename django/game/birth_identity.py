"""The agreed cosmetic birth catalog and validation; no attribute bonuses."""
from django.core.exceptions import ValidationError


def _choices(rows):
    return [dict(value=row[0], label=row[1], **({"color": row[2]} if len(row) > 2 else {})) for row in rows]


BIRTH_IDENTITY_OPTIONS = {
    "gender": _choices([("male", "Male"), ("female", "Female"), ("nonbinary", "Nonbinary"), ("custom", "Custom")]),
    "skin_tone": _choices([("very_fair", "Very fair", "#f6dfcf"), ("fair", "Fair", "#eac2a3"),
        ("light_brown", "Light brown", "#c58c63"), ("medium_brown", "Medium brown", "#a36c45"),
        ("dark_brown", "Dark brown", "#70452e"), ("very_dark", "Very dark", "#3d271e")]),
    "eye_color": _choices([("brown", "Brown", "#6b4226"), ("hazel", "Hazel", "#8e8745"),
        ("green", "Green", "#528557"), ("blue", "Blue", "#598ec4"),
        ("gray", "Gray", "#929da4"), ("amber", "Amber", "#c18b28")]),
    "hair_color": _choices([("black", "Black", "#171415"), ("dark_brown", "Dark brown", "#493025"),
        ("light_brown", "Light brown", "#916342"), ("blond", "Blond", "#dfc16b"),
        ("red", "Red", "#a84e30"), ("white", "White", "#eeeae2")]),
    "hair_length": _choices([("bald", "Bald"), ("short", "Short"), ("medium", "Medium"), ("long", "Long")]),
    "hair_texture": _choices([("straight", "Straight"), ("wavy", "Wavy"), ("curly", "Curly"), ("coily", "Coily")]),
}
IDENTITY_FIELDS = ("name", "gender", "custom_gender", "skin_tone", "eye_color", "hair_color", "hair_length", "hair_texture")


def empty_birth_identity():
    return dict.fromkeys(IDENTITY_FIELDS, "")


def validate_birth_identity(identity, *, complete=False):
    if identity == {} and not complete:
        return empty_birth_identity()
    if not isinstance(identity, dict) or set(identity) != set(IDENTITY_FIELDS):
        raise ValidationError("Supply exactly the birth identity fields.")
    if any(not isinstance(value, str) for value in identity.values()):
        raise ValidationError("Identity choices must be text.")
    result = {key: value.strip() for key, value in identity.items()}
    for key in ["name", "custom_gender"]:
        maximum = 100 if key == "name" else 40
        if len(result[key]) > maximum or any(ord(char) < 32 or ord(char) == 127 for char in result[key]):
            raise ValidationError(f"{key.replace('_', ' ').title()} must be at most {maximum} characters without control characters.")
    for key, choices in BIRTH_IDENTITY_OPTIONS.items():
        if result[key] and result[key] not in {choice["value"] for choice in choices}:
            raise ValidationError(f"Choose a valid {key.replace('_', ' ')} preset.")
    if result["gender"] != "custom" and result["custom_gender"]:
        raise ValidationError("A custom gender label is only used with Custom.")
    if result["hair_length"] == "bald" and (result["hair_color"] or result["hair_texture"]):
        raise ValidationError("Bald characters do not choose a hair color or texture.")
    if complete:
        required = ["name", "gender", "skin_tone", "eye_color", "hair_length"]
        if result["gender"] == "custom":
            required.append("custom_gender")
        if result["hair_length"] != "bald":
            required.extend(["hair_color", "hair_texture"])
        if any(not result[key] for key in required):
            raise ValidationError("Choose a name, gender, and all applicable appearance options before confirming birth.")
    return result


def birth_resources(stats):
    return {resource: {"current": stats[parent] * 10, "maximum": stats[parent] * 10}
            for resource, parent in [("health", "strength"), ("mana", "intelligence"), ("stamina", "endurance")]}
