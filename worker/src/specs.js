// The Raid Composition page's spec buttons, in link-code order: a raid link has one character per slot, the spec's
// index in RC_CODE ("-" for an empty slot). Copied from the page (tc/template2.html: RC_SPECS, RC_CODE, rcCol); if the
// page's specs or class colours change, change them here too.
export const RC_CODE = "0123456789abcdefghijklmnopqr";

const C = {
  Druid: "#FF7C0A", Hunter: "#AAD372", Mage: "#3FC7EB", Paladin: "#F48CBA", Priest: "#FFFFFF",
  Rogue: "#FFF468", Shaman: "#3190ee", Warlock: "#a1a2ff", Warrior: "#d7b285",
};

const s = (name, cls, icon) => ({ name, cls, icon, color: C[cls] });

export const SPECS = [
  s("Balance", "Druid", "spell_nature_starfall"),
  s("Feral (Bear)", "Druid", "ability_racial_bearform"),
  s("Restoration", "Druid", "spell_nature_healingtouch"),
  s("Beast Mastery", "Hunter", "ability_hunter_beasttaming"),
  s("Marksmanship", "Hunter", "ability_marksmanship"),
  s("Survival", "Hunter", "ability_hunter_swiftstrike"),
  s("Arcane", "Mage", "spell_holy_magicalsentry"),
  s("Fire", "Mage", "spell_fire_firebolt02"),
  s("Frost", "Mage", "spell_frost_frostbolt02"),
  s("Holy", "Paladin", "spell_holy_holybolt"),
  s("Protection", "Paladin", "spell_holy_devotionaura"),
  s("Retribution", "Paladin", "spell_holy_auraoflight"),
  s("Discipline", "Priest", "spell_holy_wordfortitude"),
  s("Holy", "Priest", "spell_holy_guardianspirit"),
  s("Shadow", "Priest", "spell_shadow_shadowwordpain"),
  s("Assassination", "Rogue", "ability_rogue_eviscerate"),
  s("Combat", "Rogue", "ability_backstab"),
  s("Subtlety", "Rogue", "ability_stealth"),
  s("Elemental", "Shaman", "spell_nature_lightning"),
  s("Enhancement", "Shaman", "spell_nature_lightningshield"),
  s("Restoration", "Shaman", "spell_nature_magicimmunity"),
  s("Affliction", "Warlock", "spell_shadow_deathcoil"),
  s("Demonology", "Warlock", "spell_shadow_metamorphosis"),
  s("Destruction", "Warlock", "spell_shadow_rainoffire"),
  s("Arms", "Warrior", "ability_warrior_savageblow"),
  s("Fury", "Warrior", "ability_warrior_innerrage"),
  s("Protection", "Warrior", "inv_shield_06"),
  s("Feral (Cat)", "Druid", "ability_druid_catform"),
];

export const CLASS_ORDER = Object.keys(C);
