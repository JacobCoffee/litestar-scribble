# Roadmap

This page outlines planned features and future development direction for scribbl-py.

---

## In Progress

### Scheduled Tasks

Background task processing with Huey for:

- [ ] Leaderboard resets (daily, weekly, monthly)
- [ ] Canvas cleanup (remove old/abandoned canvases)
- [ ] Session cleanup (expire old sessions)

---

## Planned Features

### Canvas Editor Enhancements

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Image Upload & Manipulation
:class-card: sd-border-0

Upload images to the canvas for tracing, reference, or composition.
Includes resize, rotate, crop, and opacity controls.
:::

:::{grid-item-card} Layer Management UI
:class-card: sd-border-0

Full layer panel with visibility toggles, opacity sliders,
blend modes, and drag-to-reorder functionality.
:::

:::{grid-item-card} Advanced Shape Tools
:class-card: sd-border-0

Polygon tool, star shapes, arrows, speech bubbles,
and custom path drawing with Bezier curves.
:::

:::{grid-item-card} Text Formatting
:class-card: sd-border-0

Font selection, text sizing, bold/italic/underline,
text alignment, and text-along-path.
:::

::::

---

### Print & Merchandise

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Image to T-Shirt
:class-card: sd-border-0

Export canvas designs directly to print-on-demand services.
Integration with providers like Printful, Printify, or custom fulfillment.

**Features:**
- Design preview on garment mockups
- Size and placement adjustment
- Direct order submission
- Design marketplace
:::

:::{grid-item-card} Sticker Sheets
:class-card: sd-border-0

Generate sticker sheet layouts from multiple drawings.
Export as print-ready PDF with cut lines.
:::

:::{grid-item-card} Canvas Prints
:class-card: sd-border-0

High-resolution export for canvas prints, posters, and framed artwork.
Multiple aspect ratios and standard print sizes.
:::

:::{grid-item-card} NFT Minting
:class-card: sd-border-0

Optional blockchain integration for minting drawings as NFTs.
Supports multiple chains and marketplaces.
:::

::::

---

### Canvas Clash Game Modes

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Multiplayer Canvas
:class-card: sd-border-0

Everyone draws simultaneously on a shared canvas.
Collaborative artwork creation with real-time sync.

**Features:**
- No turns - everyone draws at once
- Cursor labels showing who's drawing
- Layer per user option
- Time-lapse export of creation process
:::

:::{grid-item-card} Speed Draw
:class-card: sd-border-0

Rapid-fire rounds with very short timers (15-30 seconds).
Quick sketching challenges with simplified tools.
:::

:::{grid-item-card} Blind Contour
:class-card: sd-border-0

Drawing mode where you can't see your own strokes until time's up.
Classic art exercise as a party game.
:::

:::{grid-item-card} Telephone Game
:class-card: sd-border-0

Alternating draw/guess rounds where each player sees only the previous entry.
Hilarious results as the original prompt transforms.
:::

::::

---

### Collaborative Mode

Free-form collaborative whiteboard for teams and groups:

- [ ] All users draw simultaneously
- [ ] Real-time cursor positions (already implemented)
- [ ] Full layer management per user
- [ ] Infinite canvas with pan/zoom
- [ ] Sticky notes and annotations
- [ ] Video/voice chat integration
- [ ] Export to PNG/SVG (already implemented)
- [ ] Template library (wireframes, flowcharts, etc.)

---

### Social Features

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} User Profiles
:class-card: sd-border-0

Public profile pages with:
- Drawing gallery
- Game statistics
- Achievements and badges
- Following/followers
:::

:::{grid-item-card} Drawing Gallery
:class-card: sd-border-0

Browse and discover drawings from the community.
Like, comment, and share functionality.
:::

:::{grid-item-card} Drawing Challenges
:class-card: sd-border-0

Daily/weekly drawing prompts with community voting.
Themed challenges and seasonal events.
:::

:::{grid-item-card} Private Rooms
:class-card: sd-border-0

Password-protected game rooms for friends.
Invite links with expiration.
:::

::::

---

### Mobile & Desktop Apps

- [ ] Progressive Web App (PWA) with offline support
- [ ] Native iOS app with Apple Pencil support
- [ ] Native Android app with stylus support
- [ ] Desktop apps (Electron or Tauri)
- [ ] Tablet-optimized interface

---

### API & Integrations

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Webhooks
:class-card: sd-border-0

Event webhooks for canvas updates, game events, and user actions.
Integrate with Discord, Slack, or custom services.
:::

:::{grid-item-card} Public API
:class-card: sd-border-0

RESTful API with OAuth2 authentication for third-party integrations.
Rate limiting and usage quotas per API key.
:::

:::{grid-item-card} Embed Widget
:class-card: sd-border-0

Embeddable canvas widget for external websites.
Customizable size, tools, and branding.
:::

:::{grid-item-card} AI Assistance
:class-card: sd-border-0

AI-powered features:
- Auto-complete strokes
- Style transfer
- Background removal
- Image upscaling
:::

::::

---

### Infrastructure

- [ ] Redis session storage for horizontal scaling
- [ ] WebSocket message broker (Redis Pub/Sub) for multi-instance deployments
- [ ] CDN integration for static assets
- [ ] S3/GCS storage backend for large canvases
- [ ] Kubernetes Helm chart
- [ ] Terraform modules for cloud deployment

---

## Contributing

Want to help build these features? Check out the [Development Guide](guides/development.md)
and our [GitHub Issues](https://github.com/JacobCoffee/scribbl-py/issues) for open tasks.

Feature requests and ideas are welcome! Open an issue to discuss new features before
starting work to ensure alignment with the project direction.
