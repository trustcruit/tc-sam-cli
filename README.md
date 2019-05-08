**DO NOT USE, THIS IS PRE-ALPHA, HAS NO TESTS**

# tc-sam-cli

A very simplified tool wrapped around aws-sam-cli to deploy aws lambda.

Works together with [tclambda](https://pypi.org/project/tclambda/)

## Configuration

```toml
[Default]
StackName = "tc-sam-playground"
S3CodeBucket = "tc-sam-bucket"

[[ExtraPolicies]]
Effect = "Allow"
Action = ["dynamodb:*"]
Resource = "arn:aws:dynamodb:eu-west-1:1234:table/myTable"

[Functions.MyLambda]
CodeUri = "mylambda/"
Handler = "app.handler"
Runtime = "python3.7"
MemorySize = 256
Timeout = 60
ReservedConcurrentExecutions = 1

[Functions.MyLambda.Environment]
MY_KEY = "my value"

[Functions.TcLambda.Events.Ping]
Schedule = "rate(1 minute)"
Function = "ping"

[Functions.Numpy]
CodeUri = "numpy/"
Handler = "app.handler"
Runtime = "python3.7"
MemorySize = 256
Timeout = 60
Tracing = true
```

### Generate AWS SAM template

After every change in `tc-sam.toml` the template must be regenerated.

```sh
$ tc-sam generate_template > template.yml
```

It's recommended to have `template.yml` under source control.

Every Lambda has given access to each other's SQS Queue, and all Lambdas share the same S3 bucket for results. 

### Deploy

Deploy is very straightforward, it builds the sam package and deploys the cloudformation stack.

```sh
$ tc-sam deploy
```

### Environmental export

```sh
$ tc-sam env_export
TC_NUMPY_QUEUE="https://sqs.eu-west-1.amazonaws.com/123/tc-sam-playground-NumpySqs-ABC"
TC_NUMPY_BUCKET="tc-sam-playground-resultbucket-123456"
TC_MYLAMBDA_QUEUE="https://sqs.eu-west-1.amazonaws.com/123/tc-sam-playground-TcLambdaSqs-ABC"
TC_MYLAMBDA_BUCKET="tc-sam-playground-resultbucket-123456"
```

These settings can be copied to other projects that will use the aws lambdas.

### Ping all lambdas

The tclambda handler comes with a `ping` command to test if both permissions to SQS and S3 are allowed.

```sh
$ tc-sam ping
Ping NUMPY
Ping MYLAMBDA
Pong NUMPY
Pong MYLAMBDA
```
