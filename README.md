# Chaos Toolkit Extension for Open Tracing

[![Release](https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/actions/workflows/release.yaml/badge.svg)](https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/actions/workflows/release.yaml)
[![Python versions](https://img.shields.io/pypi/pyversions/chaostoolkit-opentracing.svg)](https://www.python.org/)

This project is an extension for the Chaos Toolkit for [OpenTracing][] and
[OpenTelemetry][].

[opentracing]: https://opentracing.io/
[OpenTelemetry]: https://opentelemetry.io/

Here is an example of what it could look like with the Jaeger backend.

![OpenTracing](https://github.com/chaostoolkit-incubator/chaostoolkit-opentracing/raw/master/example.png "Open Tracing with Jaeger")


## Install

This package requires Python 3.6+

To be used from your experiment, this package must be installed in the Python
environment where [chaostoolkit][] already lives.

[chaostoolkit]: https://github.com/chaostoolkit/chaostoolkit

```
$ pip install -U chaostoolkit-opentracing
```

## Usage

This extension provides two controls to trace your Chaos Toolkit experiment:

* Open Telemetry
* Open Tracing (legacy)

The only supported one is Open Telemetry as the Open Tracing is no longer
maintained.

### Open Telemetry

To enable Open Telemetry tracing, simply add the following control to
your experiment:

```json
{
    "controls": [
      {
          "name": "opentelemetry",
          "provider": {
              "type": "python",
              "module": "chaostracing.oltp"
          }
      }
    ]
}
```

We suggest you make it the first extension so it runs before and after all
other extensions.

To configure the various Open Telemetry settings, please use the standard
OLTP environment variables:

* the [sdk variables](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/sdk-environment-variables.md)
* the [exporter variables](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/exporter.md)

Mostly, you should set:

* `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` to point to your collector (for instance: http://localhost:4318/v1/traces)
* `OTEL_EXPORTER_OTLP_TRACES_HEADERS` to set any headers to pass to the exporter

NOTE: This extension supports OLTP over HTTP but not gRPC.

You can also instrument a variety of frameworks like this:


```json
{
    "controls": [
      {
          "name": "opentelemetry",
          "provider": {
              "type": "python",
              "module": "chaostracing.oltp",
              "arguments": {
                "trace_httpx": true,
                "trace_requests": true,
                "trace_botocore": true
              }
          }
      }
    ]
}
```

This will enable the according instrumentation automatically.

If you intend on using Google Cloud Platform to export your traces to, please
consider also installing the followings:

```
$ pip install opentelemetry-exporter-gcp-trace \
    opentelemetry-resourcedetector-gcp \
    opentelemetry-propagator-gcp
```

You will also need to point `GOOGLE_APPLICATION_CREDENTIALS` to a service
account which has the `roles/cloudtrace.agent` role.


### Legacy Open Tracing

This extensions supports the [Open Tracing](https://opentracing.io/) export
format but highly recommends you to switch to Open Telemetry instead. There will
be no support for Open Tracing support.

NOTE: Please see at the bottom of the page all the supported clients and
exporters this control supports.

#### Declare within the experiment

To use this control, you can declare it on a per experiment basis like this:

```json
{
    "configuration": {
        "tracing_provider": "jaeger",
        "tracing_host": "127.0.0.1",
        "tracing_port": 6831,
        "tracing_propagation": "b3"
    },
    "controls": [
        {
            "name": "opentracing",
            "provider": {
                "type": "python",
                "module": "chaostracing.control"
            }
        }
    ]
}
```

This will automatically create a [Jaeger][] client to emit traces onto the
address `127.0.0.1:6831` (over UDP).

#### Declare within the settings

You may also declare the control to be applied to all experiments by declaring
the control from within the [Chaos Toolkit settings file][ctksettings]. In that
case, you do not need to set the configuration or the controls at the
experiment level and the control will be applied to every experiments you run.

```yaml
controls:
  opentracing:
    provider:
      type: python
      module: chaostracing.control
      arguments:
        provider: jaeger
        host: 127.0.0.1
        port: 6831
        propagation: b3
```

[ctksettings]: https://docs.chaostoolkit.org/reference/usage/cli/#configure-the-chaos-toolkit
[jaeger]: https://www.jaegertracing.io/

#### Send traces from other extensions

You may also access the tracer from other extensions as follows.

For instance, assuming you have an extension that makes a HTTP call you want
to trace specifically, you could do this from your extension's code:


```python
from chaoslib import Configuration, Secrets
import requests
import opentracing

def some_function(configuration: Configuration, secrets: Secrets):
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    parent = scope.span

    with tracer.start_span("call-service1", child_of=parent) as span:
        span.set_tag('http.method','GET')
        span.set_tag('http.url', url)
        span.set_tag('span.kind', 'client')
        span.tracer.inject(span, 'http_headers', headers)

        r = requests.get(url, headers=headers)
        span.set_tag('http.status_code', r.status_code)
```

Because the opentracing exposes a noop tracer when non has been initialized,
it should be safe to have that code in your extensions without having to
determine if the extension has been enabled in the experiment.

Please note that, Open Tracing scope cannot be shared across threads
(while spans can). So, when running this in a background activity, the tracer
will not actually be set to the one that was initialized.

#### Open Tracing Provider Support

##### Jaeger tracer

The Jager tracer relies on the OpenTracing protocol which has now be superseded
by OpenTelemetry. However, we still provide support for it.

To install the necessary dependencies for the Jaeger tracer, please run:

```
$ pip install -U jaeger-client~=4.8
```

Use the following configuration:

```json
{
    "configuration": {
        "tracing_provider": "jaeger",
        "tracing_host": "127.0.0.1",
        "tracing_port": 6831,
        "tracing_propagation": "b3"
    },
    "controls": [
        {
            "name": "opentracing",
            "provider": {
                "type": "python",
                "module": "chaostracing.control"
            }
        }
    ]
}
```

## Test

To run the tests for the project execute the following:

```
$ pytest
```

## Contribute

If you wish to contribute more functions to this package, you are more than
welcome to do so. Please, fork this project, make your changes following the
usual [PEP 8][pep8] code style, sprinkling with tests and submit a PR for
review.

[pep8]: https://pycodestyle.readthedocs.io/en/latest/

The Chaos Toolkit projects require all contributors must sign a
[Developer Certificate of Origin][dco] on each commit they would like to merge
into the master branch of the repository. Please, make sure you can abide by
the rules of the DCO before submitting a PR.

[dco]: https://github.com/probot/dco#how-it-works