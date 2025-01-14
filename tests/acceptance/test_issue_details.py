from __future__ import absolute_import

import json

from datetime import datetime
from django.conf import settings
from django.utils import timezone

from sentry.testutils import AcceptanceTestCase, SnubaTestCase
from sentry.utils.samples import load_data


class IssueDetailsTest(AcceptanceTestCase, SnubaTestCase):
    def setUp(self):
        super(IssueDetailsTest, self).setUp()
        self.user = self.create_user('foo@example.com')
        self.org = self.create_organization(owner=self.user, name='Rowdy Tiger')
        self.team = self.create_team(organization=self.org, name='Mariachi Band')
        self.project = self.create_project(
            organization=self.org,
            teams=[self.team],
            name='Bengal',
        )
        self.login_as(self.user)
        self.dismiss_assistant()

    def create_sample_event(self, platform, default=None, sample_name=None):
        event_data = load_data(platform, default=default, sample_name=sample_name)
        event_data['event_id'] = 'd964fdbd649a4cf8bfc35d18082b6b0e'
        event = self.store_event(
            data=event_data,
            project_id=self.project.id,
            assert_no_errors=False,
        )
        event.datetime = datetime(2017, 9, 6, 0, 0)
        event.save()
        event.group.update(
            first_seen=datetime(2015, 8, 13, 3, 8, 25, tzinfo=timezone.utc),
            last_seen=datetime(2016, 1, 13, 3, 8, 25, tzinfo=timezone.utc),
        )
        return event

    def visit_issue(self, groupid):
        self.dismiss_assistant()
        self.browser.get(
            u'/organizations/{}/issues/{}/'.format(self.org.slug, groupid)
        )
        self.wait_until_loaded()

    def test_python_event(self):
        event = self.create_sample_event(
            platform='python',
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details python')

    def test_python_rawbody_event(self):
        event = self.create_sample_event(
            platform='python-rawbody',
        )
        self.visit_issue(event.group.id)
        self.browser.move_to('.request pre span')
        self.browser.snapshot('issue details python raw body')

    def test_python_formdata_event(self):
        event = self.create_sample_event(
            platform='python-formdata',
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details python formdata')

    def test_cocoa_event(self):
        event = self.create_sample_event(
            platform='cocoa',
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details cocoa')

    def test_unity_event(self):
        event = self.create_sample_event(
            default='unity',
            platform='csharp'
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details unity')

    def test_aspnetcore_event(self):
        event = self.create_sample_event(
            default='aspnetcore',
            platform='csharp'
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details aspnetcore')

    def test_javascript_specific_event(self):
        event = self.create_sample_event(
            platform='javascript'
        )

        self.dismiss_assistant()
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details javascript - event details')

        self.browser.find_element_by_xpath("//a//code[contains(text(), 'curl')]").click()
        self.browser.snapshot('issue details javascript - event details - curl command')

    def test_rust_event(self):
        # TODO: This should become its own "rust" platform type
        event = self.create_sample_event(
            platform='native',
            sample_name='Rust',
        )
        self.visit_issue(event.group.id)
        self.wait_until_loaded()

        self.browser.snapshot('issue details rust')

    def test_cordova_event(self):
        event = self.create_sample_event(
            platform='cordova'
        )
        self.visit_issue(event.group.id)

        self.browser.snapshot('issue details cordova')

    def test_stripped_event(self):
        event = self.create_sample_event(
            platform='pii'
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details pii stripped')

    def test_empty_exception(self):
        event = self.create_sample_event(
            platform='empty-exception'
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details empty exception')

    def test_empty_stacktrace(self):
        event = self.create_sample_event(
            platform='empty-stacktrace'
        )
        self.visit_issue(event.group.id)
        self.browser.snapshot('issue details empty stacktrace')

    def test_invalid_interfaces(self):
        event = self.create_sample_event(
            platform='invalid-interfaces'
        )
        self.visit_issue(event.group.id)

        self.browser.click('.errors-toggle')
        self.browser.wait_until('.entries > .errors ul')
        self.browser.snapshot('issue details invalid interfaces')

    def test_activity_page(self):
        event = self.create_sample_event(
            platform='python',
        )

        self.browser.get(
            u'/organizations/{}/issues/{}/activity/'.format(
                self.org.slug, event.group.id)
        )
        self.browser.wait_until_test_id('activity-item')
        self.browser.snapshot('issue activity python')

    def wait_until_loaded(self):
        self.browser.wait_until_not('.loading-indicator')
        self.browser.wait_until('.entries')
        self.browser.wait_until_test_id('linked-issues')
        self.browser.wait_until_test_id('loaded-device-name')

    def dismiss_assistant(self):
        # Forward session cookie to django client.
        self.client.cookies[settings.SESSION_COOKIE_NAME] = self.session.session_key

        res = self.client.put(
            '/api/0/assistant/',
            content_type='application/json',
            data=json.dumps({'guide_id': 1, 'status': 'viewed', 'useful': True}))
        assert res.status_code == 201

        res = self.client.put(
            '/api/0/assistant/',
            content_type='application/json',
            data=json.dumps({'guide_id': 3, 'status': 'viewed', 'useful': True}))
        assert res.status_code == 201
