# Changelog

## [Unreleased][]

[Unreleased]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.18.1..HEAD

## [0.18.1][] - 2025-06-30

[0.18.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.18.0...0.18.1

### Fixed

- Updated necessary actions for release

## [0.18.0][] - 2025-06-30

[0.18.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.17.0...0.18.0

### Fixed

- Bumped dependencies
- Only support Python 3.9+ as 3.8 is now EOL

## [0.17.0][] - 2024-04-09

[0.17.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.16.1...0.17.0

### Fixed

- Added the ctk activity name in activity spans to enrich the user readability in backend tracing systems. [#5][ctk-opentracing-5]
- Switched to [PDM][pdm] to manage project
- Drop black and isort and keep ruff only
- Drop logzero and use the builtin logging module directly

[ctk-opentracing-5]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/issues/5
[pdm]: https://pdm-project.org/en/latest

## [0.16.1][] - 2023-12-18

[0.16.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.16.0...0.16.1

### Fixed

- Hopefully fixing dependency tree of opentelemetry packages (what a mess)

## [0.16.0][] - 2023-12-18

[0.16.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.15.0...0.16.0

### Fixed

- Pin opentelemetry-instrumentation-botocore>=0.36b0 to pick correct version

## [0.15.0][] - 2023-12-01

[0.15.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.14.0...0.15.0

### Fixed

- Pin opentelemetry-exporter-prometheus>=0.36b0 as the previous pinned versions
  have been yanked from Pypi [#3521][3521]

[3521]: https://github.com/open-telemetry/opentelemetry-python/issues/3521

## [0.14.0][] - 2023-11-09

[0.14.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.13.2...0.14.0

### Changed

- Make the `AttributeError` from importing HTTPXInstrument silent because
  it will usually occur when a `gevent` environment only

### Added

- Inject bagage into root span
- Build for Python 3.11 and 3.12

## [0.13.2][] - 2023-08-03

[0.13.2]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.13.1...0.13.2

### Fixed

- Trap `AttributeError` when loading httpx. This can happen from a locust
  file as they are relying on gevent heavily which changes the socket module

## [0.13.1][] - 2023-08-02

[0.13.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.13.0...0.13.1

### Fixed

- Pass `trace_urllib3` to oltp control

## [0.13.0][] - 2023-08-02

[0.13.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.12.0...0.13.0

### Added

- Automatic tracing of urllib3

### Changed

- Do not explicitly call tracing on activities, chaoslib does it for us now

## [0.12.0][] - 2023-08-02

[0.12.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.11.0...0.12.0

### Changed

- Respect `OTEL_SERVICE_NAME` when set
- Fixed check on whether or not botocore is installed

## [0.11.0][] - 2023-08-02

[0.11.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.10.0...0.11.0

### Added

- Added specific support for Azure. Install the dependencies with `pip install chaostoolkit-opentracing[azure]`

### Changed

- Switched from flake8/pycodestyle to ruff
- Ensure there is always a good default for exporting

## [0.10.0][] - 2023-04-12

[0.10.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.9.1...0.10.0

### Added

- Added specific support for AWS

## [0.9.1][] - 2023-02-22

[0.9.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.9.0...0.9.1

### Fixed

- Missing variable declaration for GCP

### Added

- The `CHAOSTOOLKIT_OTEL_GCP_SA` and `CHAOSTOOLKIT_OTEL_GCP_PROJECT_ID`
  environment variables to pass the information of the target project

## [0.9.0][] - 2023-02-21

[0.9.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.8.2...0.9.0

### Added

- Pass GCP service account to OLTP client

## [0.8.2][] - 2023-02-03

[0.8.2]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.8.1...0.8.2

### Added

- Pre-installing common dependencies

## [0.8.1][] - 2023-02-03

[0.8.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.8.0...0.8.1

### Added

- Fix dependencies tracing and issue a proper message when they couldn't be loaded

## [0.8.0][] - 2023-02-01

[0.8.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.7.0...0.8.0

### Added

- Native support for Google Cloud PLatform Cloud Tracing

## [0.7.0][] - 2023-01-05

[0.7.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.6.0...0.7.0

### Added

- `chaostracing.oltp` contrtol to replace the legacy Open Tracing provider.
  This should be aligned with new modern approach to tracing.

## [0.6.0][] - 2022-12-01

[0.6.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.5.1...0.6.0

### Changed

- Metrics control is not implemented yet

## [0.5.1][] - 2022-12-01

[0.5.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.5.0...0.5.1

### Changed

- Revert reading headers from environment, leaving that to underlying lib

## [0.5.0][] - 2022-12-01

[0.5.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.4.0...0.5.0

- Added `exporter` as an argument of the control
- Read from `OTEL_EXPORTER_OTLP_HEADERS` and `OTEL_EXPORTER_OTLP_ENDPOINT` on OLTP HTTP


## [0.4.0][] - 2022-03-21

[0.4.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.3.1...0.4.0

### Added

-   Headers support for OLTP HTTP/GRPC exporters

## [0.3.1][] - 2021-12-13

[0.3.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.3.0...0.3.1

### Added

-   Support for `b3` propagator when using Open Telemetry

## [0.3.0][] - 2021-12-10

[0.3.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.2.1...0.3.0

### Changed

-   Added OpenTelemetry support
-   Moved to GitHub action for building/releasing
-   Set Python baseline support to 3.6
-   Using black and flake8 to lint the source

## [0.2.1][] - 2019-11-05

[0.2.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.2.0...0.2.1

### Changed

-   Clarify how to install the Jaeger client

## [0.2.0][] - 2019-11-04

[0.2.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.1.2...0.2.0

### Changed

-   Moved to OpenTracing 2 API
-   [BREAKING CHANGE] this control does not expose spans as explicit properties
    of the tracer any longer. This was due to a limitation of some of the
    Open Tracing clients (namely Jaeger). Now these clients have been updated
    to the newer version, this is not needed anymore. You can use the
    active span of the tracer as expected. This only breaks if you accessed
    directly those properties.

### Added

-   Marked with `error:true` deviated hypotheses and failed activities

## [0.1.2][] - 2018-12-06

[0.1.2]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.1.1...0.1.2

### Added

-   More configuration to the Jaeger client (to talk to Zipkin)

## [0.1.1][] - 2018-12-04

[0.1.1]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.1.0...0.1.1

### Changed

-   Open Tracing control as per the Chaos Toolkit [specification][spec]

[spec]: https://docs.chaostoolkit.org/reference/api/experiment/#controls

## [0.1.0][] - 2018-12-03

[0.1.0]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/tree/0.1.0

### Added

-   Initial release
