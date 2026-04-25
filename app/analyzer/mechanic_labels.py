MECHANIC_LABELS_RU: dict[str, str] = {
    "inventory_drag_drop": "инвентарь с drag-and-drop",
    "equipment_slots": "слоты экипировки",
    "clothing_system": "система одежды",
    "backpack_container_storage": "контейнеры, рюкзаки и хранилища",
    "crafting": "крафтинг",
    "weapons": "оружие и боевые предметы",
    "stealth": "скрытность",
    "noise_attracting_enemies": "шум, привлекающий врагов",
    "disguise_infected": "маскировка под заражённых",
    "ai_reaction_sound_visibility": "реакция ИИ на звук и видимость",
    "loot_scavenging": "лутинг и вылазки за ресурсами",
}


def mechanic_label_ru(key: str) -> str:
    return MECHANIC_LABELS_RU.get(key, key.replace("_", " "))
