# MR Custom Object — schema v1 (summary)

Full spec in Age of Joy: `Assets/ramiro/CUSTOM_OBJECT_YAML.md` (branch `0.5.0`).

## Package layout

```
{BaseDir}/MR/Custom Objects/<PackageName>/
├── object.yaml
├── <model>.glb
└── optional: *.wav, *.mp4, …
```

## placement.surfaceType

| Value | Surface |
|------:|---------|
| 0 | Floor |
| 1 | Wall |
| 2 | Ceiling |
| 3 | Free3D |
| 4 | Table |
| 5 | Object (on another prop with `providesAnchor`) |

## components

- `grab` — XR grab (`grab:` block)
- `video` — video on child mesh (`video:` block)
- `rotator` — spin GLB child (`rotator:` block)
- `animator` — play embedded GLB animation (`animator:` block)
- `light` — Unity point/spot light (`light:` block)

AOJ MR Studio edits only `object.yaml`. Room poses live in `MR/objects-layout.yaml` (not edited in v0.1).
