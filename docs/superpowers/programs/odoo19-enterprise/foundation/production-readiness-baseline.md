# Production Readiness Baseline

## Production Topology Expectations
- app layer
- database layer
- worker/cron layer
- reverse proxy
- file storage and backup scope

## Ownership
- config owner
- deployment owner
- security reviewer
- incident first responder

## Safety Baselines
- secrets must not live in source code
- backups must cover database and filestore
- restore path must be testable
- logging and monitoring must exist before go-live
- rollback path must be defined before release
