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

Currently, this extension only provides control support to send traces to
your provider during the execution of the experiment. It does not yet expose
any probes or actions per-se.

NOTE: Please see at the bottom of the page all the supported clients and
exporters this control supports.

### Declare within the experiment

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

### Declare within the settings

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

## Send traces from other extensions

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

## Open Tracing Provider Support

### Jaeger tracer

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

## OpenTelemetry provider

To install the baseline dependencies for the OpenTelemetry tracer, please run:

```
$ pip install -U opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-opentracing-shim
```

If you want the `b3` [propagator](https://opentelemetry-python.readthedocs.io/en/stable/getting-started.html#configure-your-http-propagator-b3-baggage),
please also install:

```
$ pip install opentelemetry-propagator-b3
```

#### Jaeger thrift exporter

If you want to export using the Jaeger thrift protocol, please install:

```
$ pip install opentelemetry-exporter-jaeger-thrift
```

Use the following configuration:

```json
{
    "configuration": {
        "tracing_provider": "opentelemetry",
        "tracing_opentelemetry_exporter": "jaeger-thrift",
        "tracing_host": "127.0.0.1",
        "tracing_port": 6831
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

#### Jaeger grpc exporter

If you want to export using the Jaeger grpc protocol, please install:

```
$ pip install opentelemetry-exporter-jaeger-proto-grpc
```

Use the following configuration:

```json
{
    "configuration": {
        "tracing_provider": "opentelemetry",
        "tracing_opentelemetry_exporter": "jaeger-grpc",
        "tracing_opentelemetry_collector_endpoint": "localhost:14250",
        "tracing_opentelemetry_collector_endpoint_insecure": true
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

#### OLTP grpc exporter

If you want to export using the OLTP grpc protocol, please install:

```
$ pip install opentelemetry-exporter-otlp-proto-grpc
```

Use the following configuration:

```json
{
    "configuration": {
        "tracing_provider": "opentelemetry",
        "tracing_opentelemetry_exporter": "oltp-grpc",
        "tracing_opentelemetry_collector_endpoint": "http://localhost:4317",
        "tracing_opentelemetry_collector_endpoint_insecure": true
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

#### OLTP HTTP exporter

If you want to export using the OLTP HTTP protocol, please install:

```
$ pip install opentelemetry-exporter-otlp-proto-http
```

Use the following configuration:

```json
{
    "configuration": {
        "tracing_provider": "opentelemetry",
        "tracing_opentelemetry_exporter": "oltp-http",
        "tracing_opentelemetry_collector_endpoint": "http://localhost:4318",
        "tracing_opentelemetry_collector_endpoint_insecure": true
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

## Run from containers

### From Docker

Create the following Dockerfile:

```
FROM chaostoolkit/chaostoolkit:latest

RUN pip install --no-cache-dir -q -U chaostoolkit-opentracing jaeger-client 
```

Obviously adapt the dependencies based on which provider/exporter you want to
use.


Then run this image by mounting your experiment file, for instance, something
like:

```console
$ docker run -v `pwd`/experiment.json:/home/svc/experiment.json my-image run experiment.json
```

Make sure you you correctly set the IP address of the traces agent/collector
so it can be reached. You can use `localhost` if you link networks between
containers of course too.

Here is an example of a Dockerfile to create an image with all the
providers/exporters and their dependencies:

```
FROM chaostoolkit/chaostoolkit:latest

USER root
RUN apk add --no-cache --virtual build-deps gcc g++ git libffi-dev linux-headers \
        python3-dev musl-dev && \
    apk add libstdc++ && \
    pip install --no-cache-dir -q -U pip setuptools && \
    pip install --prefer-binary --no-cache-dir -q -U chaostoolkit \
    chaostoolkit-opentracing \
    jaeger-client \
    opentelemetry-exporter-jaeger-proto-grpc \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-opentracing-shim && \
    opentelemetry-propagator-b3 && \
    apk del build-deps
USER 1001
```

### From Kubernetes

Assuming you have a container image with the `chaostoolkit-opentracing`
extension installed:


```yaml
---
kind: Deployment
apiVersion: apps/v1
metadata:
  name: ctk-tracing
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ctk-tracing
  template:
    metadata:
      name: ctk-tracing
      labels:
        app: ctk-tracing
    spec:
      containers:
      - image: my-image
        name: ctk-tracing
        imagePullPolicy: Always
        command:
          - /usr/local/bin/chaos
          - run
          - https://raw.githubusercontent.com/some/place/experiment.json

```

Obviously you can deliver the experiment as mounted file via volume as well.
Again, simply make sure you set the correct address to send the traces to.

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