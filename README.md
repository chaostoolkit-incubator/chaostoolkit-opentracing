# Chaos Toolkit Extension for Open Tracing

[![Build Status](https://travis-ci.org/chaostoolkit-incubator/chaostoolkit-opentracing.svg?branch=master)](https://travis-ci.org/chaostoolkit-incubator/chaostoolkit-opentracing)

This project is an extension for the Chaos Toolkit for [OpenTracing][].

[opentracing]: https://opentracing.io/

## Install

This package requires Python 3.5+

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

To use this control, add the following section to your experiment, at the
top-level:

```json
{
    "configuration": {
        "tracing_provider": "jaeger",
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

This will automatically create a [Jaeger][] client to emit traces onto the
address `127.0.0.1:6831`.

[jaeger]: https://www.jaegertracing.io/

You may also access the tracer from other extensions as follows:

```python
import opentracing

def some_function(...):
    opentracing.tracer
```

## Open Tracing Provider Support

For now, only the Jaeger tracer is supported but other providers will be added
as need be in the future.

### Jaeger tracer

To install the necessary dependencies for the Jaeger tracer, please run:

```
$ pip install chaostoolkit-opentracing[jaeger]
```

Unfortunately, the Jaeger client does not yet support Open Tracing 2.0.



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