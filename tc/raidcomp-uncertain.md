# Raid Composition: what to check

The page's stacking notes come from `raidcomp.json`. "Confirmed" ones come from a Forever tooltip or patch note;
everything below is **assumed**, either carried over from Classic or my best guess. Each is worth a quick question in
the class Discords. When one is answered, fix its `note` and set `status` to `"confirmed"` in `raidcomp.json`.

## Settled

- Reduced Armor: Sunder Armor and Expose Armor don't stack; Faerie Fire, Curse of Recklessness and Dust Cloud don't stack
  with each other (one -505), but do stack with Sunder/Expose: 2250 + 505 = 2755 (Fight Club / Hunter Discords). Confirmed.
- Windfury Totem and Flametongue Totem stack (both buffs now, patch notes). Confirmed.
- Healing reductions: only the strongest applies. Confirmed.
- Personal debuffs (Shadow Weaving, Improved Scorch, Improved Shadow Bolt, Winter's Chill, Stormstrike) stay off the page.
- Believed, still marked "assumed" on the page: resistance pairs don't stack; Demoralizing Shout / Roar / Screech: only the
  strongest; Inspiration and Ancestral Healing don't stack; Prayer of Spirit stacks with Dark Inspiration; two Paladins'
  Judgements of the Crusader don't stack; Curse of Tongues and Sonic Blast don't stack; Insect Swarm and Scorpid Sting
  should stack.

## Still open

1. **Hunter's Mark**: still one per target?
2. **Stamina / All Stats / Melee Attack Power / Mana Regen**: assumed to stack the Classic way (Blood Pact with Fortitude;
   Kings with Gift of the Wild; Battle Shout with Blessing of Might and Furious Howl; Wisdom with Mana Spring and Mana Tide).

## Other judgment calls

- **Personal debuffs left out**: Forever reworded Shadow Weaving, Improved Shadow Bolt, Improved Scorch, Winter's Chill
  and Stormstrike so they only help the caster ("from you", "your Cone of Cold", "can no longer be consumed by other
  players"). So they are not raid debuffs on this page. Correct?
- **Pets**: hunter and warlock pet abilities count for every Hunter / Warlock, marked with the paw. In a real raid each
  one brings a single pet (Imp for Blood Pact or Felhunter for Paranoia / Spell Lock / Devour Magic...).
- **Totems**: a Shaman is listed with every totem it can drop, although it can only have one per element down at a
  time (Windwall and Grace of Air are both Air, for example). Same for Paladin auras and Blessings.
- **Talents**: a talent counts for its own tree's spec. The other two specs are named in its tooltip as "could talent into it" (a dashed ring marks a spell or category nobody has yet but someone could) when it sits on rows
  1-4 of its tree, since 31 points in their own tree leave 20, enough for a row-4 talent (15 points + 1). Trueshot Aura for
  a Survival Hunter, Ice Block for a Fire Mage, Dark Inspiration for a Holy Priest... Rows 5-7 (Leader of the Pack, Moonkin
  Form, Power Infusion...) stay with their own spec.
- **Group icons** under each group: only the party-only buffs from the Buffs categories (Blood Pact, Dark Inspiration,
  Devotion Aura, Mana Spring, Mana Tide, Stoneskin, Windwall), like Wowhead, which skips utility totems (Tremor, Grounding,
  cleansing). Raid-wide buffs aren't repeated per group.
- **Group-only vs raid-wide** comes from today's Wowhead tooltips: auras, Mana Spring / Mana Tide / Healing Stream /
  Stoneskin / Windwall / Tremor / Grounding / cleansing totems, Aspect of the Pack, Blood Pact, Paranoia, Vampiric
  Embrace and Dark Inspiration reach only the caster's group. Battle Shout, Strength of Earth, Grace of Air, Windfury,
  Flametongue, Trueshot Aura, Leader of the Pack, Moonkin Form and the resistance buffs reach the raid (Oct 16 rewording).
- **Spellbook text is behind the patch notes** for a few spells (Battle Shout and the totems still say "party members",
  Salvation is still "Blessing of Salvation" in `spells_raw.json`). The page uses the new wording through `extra` in
  `raidcomp.json`; `sync_spells.py` may want a look.
- **Lightwell and Portal of Summoning** are left out: `spellbook.py` drops them as Season of Discovery leftovers with no
  trainer.
- **Not on the page**: Hunter tracking spells, mage portals and teleports, healing spells in general. Easy to add to a
  list in `raidcomp.json` if wanted.
- Quick Info button icon: `inv_misc_note_01` (WoW icon 134327).
