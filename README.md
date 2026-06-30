# Capsule VFX Documentation Index

Version: 1.3.0b0
Last Updated: 2026-02-23
Status: Active

---

## Start Here

- `USER_MANUAL.md`: operator workflows and day-to-day usage
- `BUILD_INSTRUCTIONS.md`: local setup and build steps
- `TESTING_GUIDE.md`: test commands and QA checklist
- `TROUBLESHOOTING_GUIDE.md`: common problems and fixes
- `CHANGELOG.md`: release and cleanup history

## Architecture And Engineering

- `SYSTEM_ARCHITECTURE.md`
- `ARCHITECTURE.md`
- `MODULE_REFERENCE.md`
- `DEVELOPER_GUIDE.md`
- `DATABASE_SCHEMA.md`
- `NETWORK_STABILITY.md`
- `DIRECTORY_STRUCTURE.md`

## Deployment And Operations

- `DEPLOYMENT_GUIDE.md`
- `DEPLOYMENT_MANUAL.md`
- `CREDENTIALS_SETUP.md`

## Feature And Planning Notes

- `VFX_PRODUCTION_LOGIC.md`
- `PRODUCTION_TOOLS_LOGIC.md`
- `FILE_MOVEMENT_LOGIC.md`
- `PLAN_INCOMING_DELIVERY_MODE.md`
- `OIIO_INTEGRATION_PLAN.md`
- `FOCUSED_ENHANCEMENT_PLAN.md`

---

## Current Product Notes (2026-02)

- `Video Editor` tab is removed.
- `Documents` tab is removed.
- Stock Browser AI-tagging modules are removed.
- Shot Review focuses on scan/render checking, annotation, approval, and lineup handoff.
- Admin Panel Live Ops reads workstation JSON from `LiveStatus` and supports fleet export.
- Attendance admin edit uses double-click in Team Overview.

---

## Documentation Scope

This folder contains both:

- active operational docs used by current builds, and
- historical design notes from earlier phases.
- archived Rez migration material in `tools/archive/rez_legacy/`.

If two docs conflict, treat these as source of truth first:

1. `CHANGELOG.md`
2. `USER_MANUAL.md`
3. `TROUBLESHOOTING_GUIDE.md`
4. `TESTING_GUIDE.md`

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

---

## Support and Help

For technical support, feature requests, or general help regarding this software, please contact the author:
**Utkarsh Tripathi** - [utkarshtripathi771@gmail.com](mailto:utkarshtripathi771@gmail.com)
