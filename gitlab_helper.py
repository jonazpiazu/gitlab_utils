import gitlab
from datetime import datetime, timedelta
import logging

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


class GitlabHelper:
    def __init__(self, gitlab_url, private_token, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info('Trying to connect to %s', gitlab_url)
        self.gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
        self.logger.info('Trying to authenticate to %s', gitlab_url)
        self.gl.auth()
        self.logger.info('Connection to %s established', gitlab_url)

    def expand_group(self, group, subgroup_id_list):
        if len(group.subgroups.list(all=True)) == 0:
            return subgroup_id_list.append(group.attributes.get('id'))
        else:
            gsgroup = group.subgroups.list(all=True)
            while gsgroup:
                self.expand_group(
                    self.gl.groups.get(gsgroup.pop().get_id()), subgroup_id_list
                )

    def get_subgroup_id_list(self, group_name):
        group_id = self.get_group_id(group_name)
        subgroup_id_list = [group_id.get_id()]
        self.expand_group(group_id, subgroup_id_list)
        return subgroup_id_list

    def get_group_id(self, group_name):
        return next(
            x
            for x in self.gl.groups.list(search=group_name)
            if x.full_name == group_name
        )

    def get_project_id_list(self, group_name, skip_archived=True):
        subgroup_id_list = self.get_subgroup_id_list(group_name)
        project_id_list = []
        for group_id in subgroup_id_list:
            group = self.gl.groups.get(group_id)
            project_id_list.extend(
                [
                    project_id
                    for project_id in group.projects.list(all=True, archived=False)
                ]
            )
            if not skip_archived:
                project_id_list.extend(
                    [
                        project_id
                        for project_id in group.projects.list(all=True, archived=True)
                    ]
                )
        return project_id_list

    def get_manageable_project(self, project):
        if isinstance(project, gitlab.v4.objects.GroupProject):
            return self.gl.projects.get(project.get_id())
        elif isinstance(project, gitlab.v4.objects.Project):
            return project
        else:
            raise Exception('Unknown project type - check API change?')

    def is_pipeline_fresh(self, project, max_days):
        manageable_project = self.get_manageable_project(project)
        max_timedelta = timedelta(days=max_days)
        if manageable_project.pipelines.list():
            last_master_pipeline = None
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
                pipeline_date = last_master_pipeline.attributes['updated_at']
                updated_at = datetime.strptime(
                    pipeline_date[0:23], '%Y-%m-%dT%H:%M:%S.%f'
                )
                if datetime.now() - updated_at > max_timedelta:
                    return dict(
                        is_fresh=False, elapsed_days=(datetime.now() - updated_at).days
                    )
                else:
                    return dict(
                        is_fresh=True, elapsed_days=(datetime.now() - updated_at).days
                    )
        return dict(is_fresh=True, elapsed_days=0)

    def get_or_create_trigger(self, project):
        trigger_description = 'bot_trigger_id'
        for t in project.triggers.list():
            if t.description == trigger_description:
                return t
        return project.triggers.create({'description': trigger_description})

    def trigger_pipeline(self, project, ref_name):
        manageable_project = self.get_manageable_project(project)
        trigger = self.get_or_create_trigger(manageable_project)
        try:
            manageable_project.trigger_pipeline(ref_name, trigger.token, variables={})
        except gitlab.exceptions.GitlabCreateError as err:
            print('There was an error when triggering the pipeline: {0}'.format(err))
