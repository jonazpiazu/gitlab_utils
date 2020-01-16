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
import collections
import csv


@click.command()
@click.argument('gitlab-url')
@click.argument('private-token')
@click.option('--group-name', required=True, help='Group name to process')
@click.option('--csv-filename', default='gitlab_stats.csv', help='Filename')
def bot_statistics(gitlab_url, private_token, group_name, csv_filename):
    # private token or personal token authentication
    gitlab_connection = GitlabHelper(gitlab_url, private_token)

    fieldnames = [
        'date',
        'total_no_of_projects',
        'no_of_non_archived_projects',
        'no_of_projects_with_pipeline',
        'no_of_projects_with_ok_pipeline',
        'no_of_projects_with_nok_pipeline',
        'no_of_projects_with_readme',
        'no_of_open_issues',
        'no_of_closed_issues',
        'no_of_open_mrs',
        'no_of_merged_mrs',
    ]
    current_stats = collections.OrderedDict.fromkeys(fieldnames, 0)

    datetime_object = datetime.datetime.now()
    current_stats['date'] = datetime_object.strftime("%d/%m/%Y")

    project_id_list = gitlab_connection.get_project_id_list(
        group_name, skip_archived=False
    )
    current_stats['total_no_of_projects'] = len(project_id_list)
    project_id_list = gitlab_connection.get_project_id_list(
        group_name, skip_archived=True
    )
    current_stats['no_of_non_archived_projects'] = len(project_id_list)

    for project in project_id_list:
        print(project.attributes.get('name'))
        manageable_project = gitlab_connection.get_manageable_project(project)
        if manageable_project.pipelines.list():
            current_stats['no_of_projects_with_pipeline'] += 1
            try:
                last_master_pipeline = next(
                    x
                    for x in manageable_project.pipelines.list()
                    if x.attributes['ref']
                    == manageable_project.attributes['default_branch']
                )
            except:
                pass
            if last_master_pipeline and last_master_pipeline.status == 'success':
                current_stats['no_of_projects_with_ok_pipeline'] += 1
            else:
                current_stats['no_of_projects_with_nok_pipeline'] += 1
        if manageable_project.attributes['readme_url']:
            current_stats['no_of_projects_with_readme'] += 1

    group_id = gitlab_connection.get_group_id(group_name)
    current_stats['no_of_open_issues'] = len(
        group_id.issues.list(state='opened', all=True)
    )
    current_stats['no_of_closed_issues'] = len(
        group_id.issues.list(state='closed', all=True)
    )
    current_stats['no_of_open_mrs'] = len(
        group_id.mergerequests.list(state='opened', all=True)
    )
    current_stats['no_of_merged_mrs'] = len(
        group_id.mergerequests.list(state='merged', all=True)
    )

    print(current_stats)

    with open(csv_filename, mode='a+') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if csv_file.tell() == 0:
            writer.writeheader()
        writer.writerow(current_stats)


if __name__ == '__main__':
    bot_statistics()
