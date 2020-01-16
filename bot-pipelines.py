#!/usr/bin/env python

#    Copyright 2019 Jon Azpiazu
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import gitlab
import os
import datetime
from gitlab_helper import GitlabHelper
import click
import logging


@click.command()
@click.option(
    '--skip-archived/--no-skip-archived', default=True, help='Skip archived projects'
)
@click.argument('gitlab-url')
@click.argument('private-token')
@click.option('--group-name', required=True, help='Group name to process')
@click.option(
    '--max-days', default=10, help='Max number of days to consider a pipeline fresh'
)
@click.option(
    '--dry-run/--no-dry-run)',
    default=False,
    help='Do not actually launch the pipelines',
)
@click.option('--log-level', default='ERROR', help='Log level')
def bot_pipelines(
    gitlab_url, private_token, skip_archived, group_name, max_days, dry_run, log_level
):
    # assuming loglevel is bound to the string value obtained from the
    # command line argument. Convert to upper case to allow the user to
    # specify --log=DEBUG or --log=debug
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=numeric_level)

    # private token or personal token authentication
    gitlab_connection = GitlabHelper(gitlab_url, private_token)

    project_id_list = gitlab_connection.get_project_id_list(group_name, skip_archived)

    for p in project_id_list:
        manageable_project = gitlab_connection.get_manageable_project(p)
        pipeline_freshness = gitlab_connection.is_pipeline_fresh(
            manageable_project, max_days
        )
        if not pipeline_freshness['is_fresh']:
            print(
                'Pipeline for project %s is %i days old, needs updating'
                % (p.attributes.get('name'), pipeline_freshness['elapsed_days'])
            )
            if not dry_run:
                print('Triggering pipeline ...')
                gitlab_connection.trigger_pipeline(
                    manageable_project, manageable_project.attributes['default_branch']
                )
            else:
                print('Dry run mode, not triggering pipeline')


if __name__ == '__main__':
    bot_pipelines()
