#!/bin/sh
# The preview's font: Roboto Condensed ExtraBold (SIL Open Font License), cut from Google Fonts' variable font,
# since resvg can't pick a weight inside a variable font. Run from worker/ (the workflow does this before building).
set -e
pip install --quiet fonttools
curl -sfL -o /tmp/RobotoCondensed.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/robotocondensed/RobotoCondensed%5Bwght%5D.ttf"
fonttools varLib.instancer /tmp/RobotoCondensed.ttf wght=800 --update-name-table -q -o src/RobotoCondensed-ExtraBold.ttf
ls -l src/RobotoCondensed-ExtraBold.ttf
