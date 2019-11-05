# Changelog

## [Unreleased][]

[Unreleased]: https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/compare/0.2.1...HEAD

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
