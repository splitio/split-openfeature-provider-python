# Split OpenFeature Provider for Python
[![Twitter Follow](https://img.shields.io/twitter/follow/splitsoftware.svg?style=social&label=Follow&maxAge=1529000)](https://twitter.com/intent/follow?screen_name=splitsoftware)

## Overview
This Provider is designed to allow the use of OpenFeature with Split, the platform for controlled rollouts, serving features to your users via the Split feature flag to manage your complete customer experience.

## Compatibility
This SDK is compatible with Python 3 and higher.

## Getting started
### Pip Installation 
```python
pip install split-openfeature==0.0.1
```
### Configure it
Below is a simple example that describes using the Split Provider. Please see the [OpenFeature Documentation](https://docs.openfeature.dev/docs/reference/concepts/evaluation-api) for details on how to use the OpenFeature SDK.

```python
from open_feature import open_feature_api
from split_openfeature import SplitProvider

open_feature_api.set_provider(SplitProvider(api_key="YOUR_API_KEY"))
```

If you are more familiar with Split or want access to other initialization options, you can provide a Split `client` to the constructor. See the [Split Java SDK Documentation](https://help.split.io/hc/en-us/articles/360020405151-Java-SDK) for more information.
```python
from open_feature import open_feature_api
from split_openfeature import SplitProvider
from splitio import get_factory

factory = get_factory("YOUR_API_KEY", config=config_file)
factory.block_until_ready(5)
open_feature_api.set_provider(SplitProvider(client=factory.client()))
```
where config_file is the Split config file you want to use

## Use of OpenFeature with Split
After the initial setup you can use OpenFeature according to their [documentation](https://docs.openfeature.dev/docs/reference/concepts/evaluation-api/).

One important note is that the Split Provider **requires a targeting key** to be set. Often times this should be set when evaluating the value of a flag by [setting an EvaluationContext](https://docs.openfeature.dev/docs/reference/concepts/evaluation-context) which contains the targeting key. An example flag evaluation is
```python
from open_feature import open_feature_api
from open_feature.evaluation_context.evaluation_context import EvaluationContext

client = open_feature_api.get_client("CLIENT_NAME")

context = EvaluationContext(targeting_key="TARGETING_KEY")
value = client.get_boolean_value("FLAG_NAME", False, context)
```
If the same targeting key is used repeatedly, the evaluation context may be set at the client level 
```python
context = EvaluationContext(targeting_key="TARGETING_KEY")
client.context = context
```
or at the OpenFeatureAPI level 
```python
from open_feature.open_feature_evaluation_context import set_api_evaluation_context

context = EvaluationContext(targeting_key="TARGETING_KEY")
set_api_evaluation_context(context)
````
If the context was set at the client or api level, it is not required to provide it during flag evaluation.

## Submitting issues
 
The Split team monitors all issues submitted to this [issue tracker](https://github.com/splitio/split-openfeature-provider-python/issues). We encourage you to use this issue tracker to submit any bug reports, feedback, and feature enhancements. We'll do our best to respond in a timely manner.

## Contributing
Please see [Contributors Guide](CONTRIBUTORS-GUIDE.md) to find all you need to submit a Pull Request (PR).

## License
Licensed under the Apache License, Version 2.0. See: [Apache License](http://www.apache.org/licenses/).

## About Split
 
Split is the leading Feature Delivery Platform for engineering teams that want to confidently deploy features as fast as they can develop them. Split’s fine-grained management, real-time monitoring, and data-driven experimentation ensure that new features will improve the customer experience without breaking or degrading performance. Companies like Twilio, Salesforce, GoDaddy and WePay trust Split to power their feature delivery.
 
To learn more about Split, contact hello@split.io, or get started with feature flags for free at https://www.split.io/signup.
 
Split has built and maintains SDKs for:
 
* Java [Github](https://github.com/splitio/java-client) [Docs](https://help.split.io/hc/en-us/articles/360020405151-Java-SDK)
* Javascript [Github](https://github.com/splitio/javascript-client) [Docs](https://help.split.io/hc/en-us/articles/360020448791-JavaScript-SDK)
* Node [Github](https://github.com/splitio/javascript-client) [Docs](https://help.split.io/hc/en-us/articles/360020564931-Node-js-SDK)
* .NET [Github](https://github.com/splitio/dotnet-client) [Docs](https://help.split.io/hc/en-us/articles/360020240172--NET-SDK)
* Ruby [Github](https://github.com/splitio/ruby-client) [Docs](https://help.split.io/hc/en-us/articles/360020673251-Ruby-SDK)
* PHP [Github](https://github.com/splitio/php-client) [Docs](https://help.split.io/hc/en-us/articles/360020350372-PHP-SDK)
* Python [Github](https://github.com/splitio/python-client) [Docs](https://help.split.io/hc/en-us/articles/360020359652-Python-SDK)
* GO [Github](https://github.com/splitio/go-client) [Docs](https://help.split.io/hc/en-us/articles/360020093652-Go-SDK)
* Android [Github](https://github.com/splitio/android-client) [Docs](https://help.split.io/hc/en-us/articles/360020343291-Android-SDK)
* iOS [Github](https://github.com/splitio/ios-client) [Docs](https://help.split.io/hc/en-us/articles/360020401491-iOS-SDK)
 
For a comprehensive list of open source projects visit our [Github page](https://github.com/splitio?utf8=%E2%9C%93&query=%20only%3Apublic%20).
 
**Learn more about Split:**
 
Visit [split.io/product](https://www.split.io/product) for an overview of Split, or visit our documentation at [help.split.io](http://help.split.io) for more detailed information.

