# Automatic framing examples

Created 2026-11-07 with the built-in ImageGen tool. Final assets are
`framing-0.png` (wide room view) and `framing-1.png` (a reframed view within the
2x zoom limit). The person remains off-centre because the original frame places
her close to its left edge.
The initial photographic study was replaced by cartoons following user feedback.

Initial composition prompt:

> Use case: ui-mockup. Asset type: a photographic illustration inside a video-call settings choice card. Create one clean wide 16:9 photograph of a friendly older adult seated in an armchair at the FAR LEFT side of a tidy, softly lit living room, facing the camera with a relaxed expression. Their whole seated body and chair are visible, with generous headroom and a large area of empty living room on the right. This represents a webcam image BEFORE automatic framing. A realistic, simple room with a pale wall and one plant; muted warm neutral tones, good facial contrast, no distracting decoration. The person must be clearly off-centre, fairly small in frame, about one third of the frame height. Straight-on webcam viewpoint. Photograph only, edge-to-edge rectangular composition. No text, no icons, no arrows, no borders, no UI, no watermark.

Cartoon conversion, using the initial study as reference:

> Use case: style-transfer. Turn this scene into a friendly, polished CARTOON illustration for a small settings card. Keep the wide 16:9 composition and the same older woman with short grey hair, rust-coloured sweater and cream trousers seated in the armchair at the FAR LEFT, with the big empty wall on the right. Simplify everything to rounded shapes, clean soft outlines, flat warm pastel colours and very light shading. Clearly illustrated rather than photographic, cheerful but calm, readable at thumbnail size. Keep her whole body and chair visible. Keep the plant and room geometry; remove tiny texture/detail. No text, symbols, arrows, border, buttons, or interface. This is the BEFORE automatic framing image. Opaque background.

Initial reframed study, subsequently replaced because it zoomed too far:

> Use case: precise-object-edit. This is the paired AFTER automatic framing illustration for the supplied BEFORE cartoon. Keep exactly the same cheerful older woman, face, short grey hair, rust sweater, cream trousers, armchair, plant, palette and cartoon drawing style. Change only the camera framing: crop/zoom and recenter on the seated woman so her FACE is horizontally centered, with modest headroom, her head and upper torso much larger and clear. A head-and-torso video-call crop, cutting off legs and most of chair. Keep the same room behind her, only a small part of the plant visible at the right edge. Output a wide 16:9 rectangle. Do not move the woman within the room or redesign her; portray a camera crop of the same original scene. No text, arrows, UI, borders, watermark or symbols.

Final companion prompt, using the wide cartoon as reference:

> Use case: precise-object-edit. Create the AFTER automatic framing companion of this same wide cartoon, respecting a STRICT MAXIMUM 2x zoom, not a closeup. Treat this as a crop of the input, not a new drawing: use a crop approximately half of the original image width and half its height, from the LEFT part of the original. On the 1672 by 941 reference this corresponds approximately to x=0..836 and y=300..770. Preserve exactly the same woman, room, colours, chair and art style. The woman should remain slightly LEFT of centre because a 2x crop cannot fully recenter a person so near the original edge. Show her full head, torso, lap and knees plus much of the armchair and the plant to her right, with substantial wall still visible. Her face should be no more than twice its original proportion of frame, about 20 percent of image height, clearly NOT a head-and-shoulders portrait. Output wide 16:9. Do not invent extra room, change pose, or redraw face. No text, UI, arrows, border or watermark.
