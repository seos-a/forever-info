"""Text clean-ups shared by build.py and changelog.py."""
import re

def clean_html(desc):
    """Wowhead occasionally leaves HTML in a description (Weaponmaster): a double <br /> starts a new line,
    a single one is just a line wrap, and tags such as <span> are dropped."""
    desc = re.sub(r'\s*(<br\s*/?>\s*){2,}', '\n', desc)
    desc = re.sub(r'\s*<br\s*/?>\s*', ' ', desc)
    desc = re.sub(r'<[^>]+>', '', desc)
    return re.sub(r'[ \t]{2,}', ' ', desc)

def tidy_formula(desc):
    """Wowhead sometimes leaves a damage/healing formula in a talent's text. Write it the way the site always has:
    "[32 / Ferocity: 48 + (Ranged Attack Power * (0.05))]" -> "32 (plus 5% of your Ranged Attack Power)" (the
    "/ Talent: n" parts are the value with other talents taken), "[(172 + (Healing * 0.429)) * (1 * 1)]" ->
    "172 (plus about 43% of your bonus healing)"."""
    desc = re.sub(r'\[(\d+(?:\.\d+)?)(?: / [^\]/:]+: \d+(?:\.\d+)?)+', lambda m: '[' + m.group(1), desc)
    def pct(x):
        v = float(x) * 100
        return (f'about {round(v)}' if abs(v - round(v)) > 0.05 else f'{round(v)}') + '%'
    desc = re.sub(r'\[\(?(\d+(?:\.\d+)?) \+ \(Healing \* \(?([\d.]+)\)?\)\)?(?: \* \(1 \* 1\))?\]',
                  lambda m: f'{m.group(1)} (plus {pct(m.group(2))} of your bonus healing)', desc)
    desc = re.sub(r'\[\(?(\d+(?:\.\d+)?) \+ \(((?:Ranged )?Attack Power|Spell Power|[A-Z][a-z]+ spell power) \* \(?([\d.]+)\)?\)\)?(?: \* \(1 \* 1\))?\]',
                  lambda m: f'{m.group(1)} (plus {pct(m.group(3))} of your {m.group(2)})', desc)
    return desc
