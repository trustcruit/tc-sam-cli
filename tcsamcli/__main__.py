#!/usr/bin/env python
import json
import sys
from operator import itemgetter

import click
import toml

import boto3
import sh
import tclambda.auto_functions
from jinja2 import Environment, PackageLoader
from tclambda.function import LambdaFunction

cloudformation = boto3.client("cloudformation")


@click.group()
def cli():
    pass


@cli.command()
@click.option("--output", type=click.File("w"), default=sys.stdout)
def generate_template(output):
    with open("tc-sam.toml") as f:
        config = toml.load(f)

    loader = PackageLoader("tcsamcli", "templates")
    env = Environment(
        loader=loader, autoescape=False, keep_trailing_newline=True, trim_blocks=True
    )
    template = env.get_template("template.yaml.j2")
    output.write(template.render(config=config["Functions"]))


@cli.command()
@click.option(
    "--no-build", is_flag=True, default=False, help="Skip building the packages."
)
def deploy(**kwargs):
    with open("tc-sam.toml") as f:
        config = toml.load(f)

    stack_name = config["Default"]["StackName"]
    s3_bucket = config["Default"]["S3CodeBucket"]
    template_file = ".aws-sam/packaged.yaml"

    try:
        if not kwargs.get("no_build"):
            sh.sam.build(_fg=True)
        sh.sam.package(
            s3_bucket=s3_bucket, output_template_file=template_file, _fg=True
        )
        sh.sam.deploy(
            template_file=template_file,
            stack_name=stack_name,
            capabilities="CAPABILITY_IAM",
            _fg=True,
        )
    except Exception:
        pass


@cli.command()
@click.argument("module")
@click.option("--input-file", type=click.File("r"))
@click.option("--function-name")
@click.option("--args", type=json.loads, default="[]")
@click.option("--kwargs", type=json.loads, default="{}")
@click.option("--delay", type=float, default=5)
def invoke(module, input_file, function_name, args, kwargs, delay):
    lf = getattr(tclambda.auto_functions, module)
    if input_file:
        data = json.load(input_file)
        function_name = data["function_name"]
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
    result = getattr(lf, function_name)(*args, **kwargs)
    click.echo(result.result(delay=delay))


@cli.command()
def env_export():
    with open("tc-sam.toml") as f:
        config = toml.load(f)

    stack_name = config["Default"]["StackName"]
    response = cloudformation.describe_stacks(StackName=stack_name)
    stack = response["Stacks"][0]
    outputs = dict(map(itemgetter("OutputKey", "OutputValue"), stack["Outputs"]))
    result_bucket = outputs["ResultBucket"]
    for key, value in outputs.items():
        if key.endswith("Queue"):
            key = key[: -len("Queue")].upper()
            click.echo(f'TC_{key}_QUEUE="{value}"')
            click.echo(f'TC_{key}_BUCKET="{result_bucket}"')


@cli.command()
def ping():
    with open("tc-sam.toml") as f:
        config = toml.load(f)

    stack_name = config["Default"]["StackName"]
    response = cloudformation.describe_stacks(StackName=stack_name)
    stack = response["Stacks"][0]
    outputs = dict(map(itemgetter("OutputKey", "OutputValue"), stack["Outputs"]))
    result_bucket = outputs["ResultBucket"]
    pings = []
    for key, value in outputs.items():
        if key.endswith("Queue"):
            key = key[: -len("Queue")].upper()
            lf = LambdaFunction(value, result_bucket)
            result = lf.ping()
            pings.append((key, result))
            click.secho(f"Ping {key}")
    for key, ping in pings:
        try:
            if ping.result(delay=0.5) == "pong":
                click.secho(f"Pong {key}", fg="green")
            else:
                click.secho(f"No pong {key}: {ping.result()}")
        except TimeoutError as e:
            click.secho(f"Timeout {key}: {e}")
        except Exception as e:
            click.secho(f"Error {key}: {e}")


if __name__ == "__main__":
    cli()
