# Command Input Reference

This guide provides detailed documentation for the command-based music input system.

## Overview

The Command Input panel allows you to enter music notation using simple text commands. This approach is inspired by text-based notation systems like Lilypond, ABC notation, and gabc (for chant).

## Basic Syntax

Each line typically represents one musical element:

```
ELEMENT [DURATION] ["LYRIC"]
```

## Notes

### Pitch Specification

Notes are specified with three components:

1. **Letter name**: C, D, E, F, G, A, B (case-insensitive)
2. **Accidentals** (optional):
   - `#` or `s` = sharp
   - `##` or `ss` = double sharp
   - `b` = flat
   - `bb` = double flat
   - `n` = natural (explicit)
3. **Octave number**: 0-9 (4 = middle C octave)

### Examples

```
C4        # Middle C
D#5       # D sharp, one octave above middle C
Bb3       # B flat, one octave below middle C
F##4      # F double sharp (same as G)
Gn4       # G natural (explicitly natural)
```

### Octave Reference

| Octave | Range | Piano Reference |
|--------|-------|-----------------|
| 0 | C0-B0 | Lowest piano notes |
| 1 | C1-B1 | Low bass |
| 2 | C2-B2 | Bass clef |
| 3 | C3-B3 | Below middle C |
| 4 | C4-B4 | Middle C octave |
| 5 | C5-B5 | Treble clef |
| 6 | C6-B6 | High treble |
| 7 | C7-B7 | Highest piano notes |

## Durations

### Duration Codes

| Code | American Name | British Name | Value |
|------|---------------|--------------|-------|
| `w` | Whole | Semibreve | 4 beats |
| `h` | Half | Minim | 2 beats |
| `q` | Quarter | Crotchet | 1 beat |
| `e` | Eighth | Quaver | 1/2 beat |
| `s` | Sixteenth | Semiquaver | 1/4 beat |
| `t` | Thirty-second | Demisemiquaver | 1/8 beat |

### Dotted Notes

Add `.` after the duration for dotted notes:

```
C4 h.     # Dotted half note (3 beats)
D4 q.     # Dotted quarter note (1.5 beats)
E4 e.     # Dotted eighth note (3/4 beat)
```

### Double-Dotted Notes

Use `..` for double-dotted notes:

```
C4 h..    # Double-dotted half (3.5 beats)
```

### Examples

```
C4 w      # C whole note
D4 h      # D half note
E4 q      # E quarter note
F4 e      # F eighth note
G4 s      # G sixteenth note
A4 h.     # A dotted half note
```

## Rests

Use `r` or `R` for rests:

```
r q       # Quarter rest
r h       # Half rest
r w       # Whole rest
r e       # Eighth rest
```

## Chords

Enclose chord notes in square brackets:

```
[C4 E4 G4] q         # C major chord, quarter note
[D4 F4 A4] h         # D minor chord, half note
[G3 B3 D4 F4] q      # G7 chord
```

### Chord with Lyrics

```
[C4 E4 G4] q "Ah"    # Chord with lyric
```

## Lyrics

Enclose lyrics in double quotes after the duration:

```
C4 q "Hel-"
D4 q "lo"
E4 h "World"
```

### Syllable Hyphens

Use hyphens to indicate syllable breaks for melismas:

```
C4 q "A-"
D4 q "ma-"
E4 q "zing"
F4 q "Grace"
```

### Multi-Note Syllables (Slurs)

When one syllable spans multiple notes, only the first note gets the lyric:

```
C4 e "Glo-"
D4 e           # Part of same syllable (melisma)
E4 q "ry"
```

### Special Characters in Lyrics

Escape quotes within lyrics:

```
C4 q "He said \"Hello\""
```

## Barlines

| Symbol | Type |
|--------|------|
| `\|` or `bar` | Single barline |
| `\|\|` or `dbar` | Double barline |
| `\|\|\|` or `final` | Final barline |
| `:\|` | Repeat end |
| `\|:` | Repeat start |
| `:\|:` | Repeat both |

### Examples

```
C4 q D4 q E4 q F4 q |         # Single barline
G4 q A4 q B4 q C5 q ||        # Double barline
C5 w |||                       # Final barline
```

## Commands

### Key Signature

```
key: C major
key: G major
key: D minor
key: Bb major
key: F# minor
```

### Time Signature

```
time: 4/4
time: 3/4
time: 6/8
time: 2/2
time: cut       # Cut time (2/2)
time: common    # Common time (4/4)
```

### Tempo

```
tempo: 120              # Quarter note = 120 BPM
tempo: 60               # Quarter note = 60 BPM
tempo: Allegro          # Named tempo
tempo: Andante
```

### Clef

```
clef: treble
clef: bass
clef: alto
clef: tenor
clef: percussion
```

### Title and Metadata

```
title: Amazing Grace
composer: John Newton
arranger: Traditional
```

## Complete Examples

### Simple Melody

```
# Twinkle Twinkle Little Star
key: C major
time: 4/4
tempo: 100

C4 q "Twin-"
C4 q "kle"
G4 q "twin-"
G4 q "kle"
|
A4 q "lit-"
A4 q "tle"
G4 h "star"
||
```

### With Chords

```
# Simple Chord Progression
key: C major
time: 4/4

[C4 E4 G4] h
[C4 E4 G4] h
|
[F4 A4 C5] h
[F4 A4 C5] h
|
[G4 B4 D5] h
[G4 B4 D5] h
|
[C4 E4 G4] w
||
```

### Hymn with Lyrics

```
# Amazing Grace (First Verse)
title: Amazing Grace
composer: John Newton
key: G major
time: 3/4
tempo: 80

r h
G4 q "A-"
|
B4 q "ma-"
r e
B4 e "zing"
D5 h "Grace"
|
D5 q "how"
C5 e "sweet"
B4 e
B4 h "the"
G4 q "sound"
|
G4 h "that"
A4 q "saved"
|
B4 q "a"
r e
B4 e "wretch"
A4 h "like"
G4 q "me"
||
```

## Advanced Features

### Dynamics (Coming Soon)

```
C4 q pp          # Pianissimo
D4 q mf          # Mezzo-forte
E4 q ff          # Fortissimo
```

### Articulations (Coming Soon)

```
C4 q staccato
D4 q accent
E4 q tenuto
```

### Tuplets (Coming Soon)

```
tuplet 3 {
  C4 e D4 e E4 e
}
```

## Tips and Best Practices

1. **Use comments**: Add `#` for notes to yourself
2. **Group related measures**: Blank lines help readability
3. **Be consistent with spacing**: One space between elements
4. **Test incrementally**: Process after each section to catch errors
5. **Start simple**: Add complexity gradually

## Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| "Invalid pitch" | Pitch format not recognized | Check note name and octave |
| "Unknown duration" | Duration code not valid | Use w, h, q, e, s, t |
| "Unclosed bracket" | Chord brackets mismatch | Add missing `]` |
| "Unclosed quote" | Lyric quotes mismatch | Add missing `"` |

## Keyboard Shortcuts in Command Panel

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Process commands |
| `Ctrl+/` | Toggle comment |
| `Tab` | Indent line |
| `Shift+Tab` | Unindent line |

---

For more examples, see the `examples/` folder in the repository.
