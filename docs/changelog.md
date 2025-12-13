# Changelog

All notable changes to scribbl-py will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial release of scribbl-py
- Core canvas and element models (Canvas, Stroke, Shape, Text, Point)
- Storage backends (InMemoryStorage, DatabaseStorage)
- CanvasService for business logic
- REST API for canvas and element CRUD operations
- WebSocket real-time collaboration
- Canvas Clash multiplayer drawing game
- OAuth authentication (Google, Discord, GitHub)
- Export to JSON, SVG, and PNG formats
- HTMX + Tailwind CSS + DaisyUI frontend
- Docker deployment support
- Structured logging with correlation IDs
- Rate limiting
- Health check endpoints
- Telemetry integration (Sentry, PostHog)
- CLI commands for database queries

## [0.1.0] - 2024-12-13

### Added

- Initial project scaffolding
- Core domain models
- Basic API endpoints
- WebSocket support
- Database persistence with SQLAlchemy
- Canvas operations (z-index, undo/redo, grouping)
- Export functionality
- Authentication system
- Game mode (Canvas Clash)
- Production deployment configuration

[Unreleased]: https://github.com/JacobCoffee/scribbl-py/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JacobCoffee/scribbl-py/releases/tag/v0.1.0
