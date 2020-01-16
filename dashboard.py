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
import json
from jinja2 import Environment, FileSystemLoader
import os
import datetime
from gitlab_helper import GitlabHelper
import click


@click.command()
@click.option(
    '--skip-archived/--no-skip-archived',
    default=True,
    help='Skip archived projects in the generated dashboard',
)
@click.argument('gitlab-url')
@click.argument('private-token')
@click.option('--group-name', required=True, help='Group name to process')
def generate_dashboard(gitlab_url, private_token, skip_archived, group_name):
    # private token or personal token authentication
    gitlab_connection = GitlabHelper(gitlab_url, private_token)

    datetime_object = datetime.datetime.now()
    generated_time = datetime_object.strftime("%d/%m/%Y, %H:%M:%S")

    project_id_list = gitlab_connection.get_project_id_list(group_name, skip_archived)

    proj_list = []
    for project in project_id_list:
        print(project.attributes.get('name'))

        manageable_project = gitlab_connection.get_manageable_project(project)
        proj_data = manageable_project.attributes
        proj_data["pipeline_status"] = "None"
        proj_data["pipeline_web_url"] = "none"
        proj_data["master_pipeline_status"] = "None"
        proj_data["master_pipeline_web_url"] = "none"
        if manageable_project.pipelines.list():
            proj_data["pipeline_status"] = manageable_project.pipelines.list()[0].status
            proj_data["pipeline_web_url"] = manageable_project.pipelines.list()[
                0
            ].web_url
            try:
                last_master_pipeline = next(
                    x
                    for x in manageable_project.pipelines.list()
                    if x.attributes['ref']
                    == manageable_project.attributes['default_branch']
                )
            except:
                pass
            if last_master_pipeline:
                proj_data["master_pipeline_status"] = last_master_pipeline.status
                proj_data["master_pipeline_web_url"] = last_master_pipeline.web_url
        proj_list.append(proj_data)

    json_data = json.dumps(proj_list)

    with open('data.json', 'w') as outfile:
        json.dump(json_data, outfile)

    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('dashboard.html')

    filename = os.path.join(root, 'html', 'dashboard.html')

    with open(filename, 'w') as fh:
        fh.write(template.render(projects=proj_list, generated_time=generated_time))


if __name__ == '__main__':
    generate_dashboard()
