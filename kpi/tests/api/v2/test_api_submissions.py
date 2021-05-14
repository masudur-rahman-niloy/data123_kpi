# coding: utf-8
import copy
import json
import uuid
from datetime import datetime

import pytz
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from kpi.constants import (
    PERM_ADD_SUBMISSIONS,
    PERM_CHANGE_ASSET,
    PERM_CHANGE_SUBMISSIONS,
    PERM_DELETE_SUBMISSIONS,
    PERM_PARTIAL_SUBMISSIONS,
    PERM_VALIDATE_SUBMISSIONS,
    PERM_VIEW_ASSET,
    PERM_VIEW_SUBMISSIONS,
)
from kpi.models import Asset
from kpi.models.object_permission import get_anonymous_user
from kpi.tests.base_test_case import BaseTestCase
from kpi.urls.router_api_v2 import URL_NAMESPACE as ROUTER_URL_NAMESPACE


class BaseSubmissionTestCase(BaseTestCase):
    """
    DataViewset uses `BrowsableAPIRenderer` as the first renderer.
    Force JSON to test the API by specifying `format`, `HTTP_ACCEPT` or
    `content_type`
    """

    fixtures = ["test_data"]

    URL_NAMESPACE = ROUTER_URL_NAMESPACE

    def setUp(self):
        self.client.login(username="someuser", password="someuser")
        self.someuser = User.objects.get(username="someuser")
        self.anotheruser = User.objects.get(username="anotheruser")
        content_source_asset = Asset.objects.get(id=1)
        self.asset = Asset.objects.create(content=content_source_asset.content,
                                          owner=self.someuser,
                                          asset_type='survey')

        self.asset.deploy(backend='mock', active=True)
        self.asset.save()

        v_uid = self.asset.latest_deployed_version.uid
        # TODO tests with more submissions
        self.submissions = [
            {
                "__version__": v_uid,
                "q1": "a1",
                "q2": "a2",
                "_id": 1,
                "instanceID": f'uuid:{uuid.uuid4()}',
                "_validation_status": {
                    "by_whom": "someuser",
                    "timestamp": 1547839938,
                    "uid": "validation_status_on_hold",
                    "color": "#0000ff",
                    "label": "On Hold"
                },
                "_submitted_by": ""
            },
            {
                "__version__": v_uid,
                "q1": "a3",
                "q2": "a4",
                "_id": 2,
                "instanceID": f'uuid:{uuid.uuid4()}',
                "_validation_status": {
                    "by_whom": "someuser",
                    "timestamp": 1547839938,
                    "uid": "validation_status_approved",
                    "color": "#0000ff",
                    "label": "Approved"
                },
                "_submitted_by": "someuser"
            }
        ]
        self.asset.deployment.mock_submissions(self.submissions)
        self.asset.deployment.set_namespace(self.URL_NAMESPACE)
        self.submission_url = self.asset.deployment.submission_list_url
        self._deployment = self.asset.deployment
        self._id_fieldname = self.asset.deployment.INSTANCE_ID_FIELDNAME

    def _log_in_as_another_user(self):
        """
        Helper to switch user from `someuser` to `anotheruser`.
        """
        self.client.logout()
        self.client.login(username="anotheruser", password="anotheruser")


class BulkDeleteSubmissionsApiTests(BaseSubmissionTestCase):

    # TODO, Add tests with ids and query

    def setUp(self):
        super().setUp()
        self.submissions_url = reverse(
            self._get_endpoint('submission-list'),
            kwargs={'parent_lookup_asset': self.asset.uid, 'format': 'json'},
        )
        self.submission_bulk_url = reverse(
            self._get_endpoint('submission-bulk'),
            kwargs={
                'parent_lookup_asset': self.asset.uid,
            },
        )

    def test_delete_submissions_owner(self):
        data = {'payload': {'confirm': True}}
        response = self.client.delete(self.submission_bulk_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.submissions_url, {'format': 'json'})
        # FIXME get submission count for user from Mockbackend
        self.assertEqual(response.data['count'], 0)

    def test_delete_submissions_anonymous(self):
        self.client.logout()
        data = {'payload': {'confirm': True}}
        response = self.client.delete(self.submission_bulk_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_submissions_not_shared_other(self):
        self._log_in_as_another_user()
        data = {'payload': {'confirm': True}}
        response = self.client.delete(self.submission_bulk_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_submissions_shared_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_DELETE_SUBMISSIONS)
        self._log_in_as_another_user()
        data = {'payload': {'confirm': True}}

        response = self.client.delete(self.submission_bulk_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.submissions_url, {'format': 'json'})
        # FIXME get submission count for user from Mockbackend
        self.assertEqual(response.data['count'], 0)

    def test_delete_submissions_with_partial_perms(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_DELETE_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }

        # Allow anotheruser to delete someuser's data
        self.asset.assign_perm(
            self.anotheruser,
            PERM_PARTIAL_SUBMISSIONS,
            partial_perms=partial_perms,
        )

        # Get number of submissions anotheruser is allowed to see
        response = self.client.get(self.submissions_url, {'format': 'json'})
        another_submissions_count = response.data['count']

        # Try first submission submitted by unknown
        # TODO get submissions submitted by unknown dynamically
        data = {
            'payload': {
                'submission_ids': [1]
            }
        }
        response = self.client.delete(self.submission_bulk_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try second submission submitted by someuser
        # TODO get submissions submitted by someuser dynamically
        data = {
            'payload': {
                'submission_ids': [2]
            }
        }
        response = self.client.delete(self.submission_bulk_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.submissions_url, {'format': 'json'})
        # FIXME get submission count for user from Mockbackend
        self.assertEqual(response.data['count'], 0)

        # Ensure another only deleted their submissions
        self.login_as_other_user('someuser', 'someuser')
        response = self.client.get(self.submissions_url, {'format': 'json'})
        for submission in response.data['results']:
            self.assertNotEqual(submission['_submitted_by'], 'someuser')


class SubmissionApiTests(BaseSubmissionTestCase):

    def test_cannot_create_submission(self):
        v_uid = self.asset.latest_deployed_version.uid
        submission = {
            "q1": "a5",
            "q2": "a6",
        }
        # Owner
        response = self.client.post(self.submission_url, data=submission)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Shared
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.post(self.submission_url, data=submission)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Anonymous
        self.client.logout()
        response = self.client.post(self.submission_url, data=submission)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_submissions_owner(self):
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('results'), self.submissions)
        self.assertEqual(response.data.get('count'), len(self.submissions))

    def test_list_submissions_owner_with_params(self):
        """
        The mock backend doesn't support all of these parameters, but we can at
        least check that they pass through
        `BaseDeploymentBackend.validate_submission_list_params()` without error
        """
        response = self.client.get(
            self.submission_url, {
                'format': 'json',
                'start': 1,
                'limit': 1,
                'sort': '{"dummy": -1}',
                'fields': '{"dummy": 1}',
                'query': '{"dummy": "make me a match"}',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_submissions_limit(self):
        limit = settings.SUBMISSION_LIST_LIMIT
        excess = 10
        asset = Asset.objects.create(
            name='Lots of submissions',
            owner=self.asset.owner,
            content={'survey': [{'name': 'q', 'type': 'integer'}]},
        )
        asset.deploy(backend='mock', active=True)
        asset.deployment.set_namespace(self.URL_NAMESPACE)
        latest_version_uid = asset.latest_deployed_version.uid
        submissions = [
            {
                '__version__': latest_version_uid,
                'q': i,
            } for i in range(limit + excess)
        ]
        asset.deployment.mock_submissions(submissions)

        # Server-wide limit should apply if no limit specified
        response = self.client.get(
            asset.deployment.submission_list_url, {'format': 'json'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), limit)
        # Limit specified in query parameters should not be able to exceed
        # server-wide limit
        response = self.client.get(
            asset.deployment.submission_list_url,
            {'limit': limit + excess, 'format': 'json'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), limit)

    def test_list_submissions_not_shared_other(self):
        self._log_in_as_another_user()
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_submissions_shared_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('results'), self.submissions)
        self.assertEqual(response.data.get('count'), len(self.submissions))

    def test_list_submissions_with_partial_permissions(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_VIEW_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.asset.assign_perm(self.anotheruser, PERM_PARTIAL_SUBMISSIONS,
                               partial_perms=partial_perms)
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.asset.deployment.submission_count == 2)
        # User `anotheruser` should only see submissions where `submitted_by`
        # is filled up and equals to `someuser`
        self.assertTrue(response.data.get('count') == 1)
        submission = response.data.get('results')[0]
        self.assertTrue(submission.get('_submitted_by') == self.someuser.username)

    def test_list_submissions_anonymous(self):
        self.client.logout()
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_submissions_anonymous_asset_publicly_shared(self):
        self.client.logout()
        anonymous_user = get_anonymous_user()
        self.asset.assign_perm(anonymous_user, PERM_VIEW_SUBMISSIONS)
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.asset.remove_perm(anonymous_user, PERM_VIEW_SUBMISSIONS)

    def test_list_submissions_authenticated_asset_publicly_shared(self):
        """ https://github.com/kobotoolbox/kpi/issues/2698 """

        anonymous_user = get_anonymous_user()
        self._log_in_as_another_user()

        # Give the user who will access the public data--without any explicit
        # permission assignment--their own asset. This is needed to expose a
        # flaw in `ObjectPermissionMixin.__get_object_permissions()`
        Asset.objects.create(name='i own it', owner=self.anotheruser)

        # `self.asset` is owned by `someuser`; `anotheruser` has no
        # explicitly-granted access to it
        self.asset.assign_perm(anonymous_user, PERM_VIEW_SUBMISSIONS)
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.asset.remove_perm(anonymous_user, PERM_VIEW_SUBMISSIONS)

    def test_list_submissions_asset_publicly_shared_and_shared_with_user(self):
        """
        Running through behaviour described in issue kpi/#2870 where an asset
        that has been publicly shared and then explicity shared with a user, the
        user has lower permissions than an anonymous user and is therefore
        unable to view submission data.
        """

        self._log_in_as_another_user()
        anonymous_user = get_anonymous_user()

        assert self.asset.has_perm(self.anotheruser, PERM_VIEW_ASSET) == False
        assert PERM_VIEW_ASSET not in self.asset.get_perms(self.anotheruser)
        assert self.asset.has_perm(self.anotheruser, PERM_CHANGE_ASSET) == False
        assert PERM_CHANGE_ASSET not in self.asset.get_perms(self.anotheruser)

        self.asset.assign_perm(self.anotheruser, PERM_CHANGE_ASSET)

        assert self.asset.has_perm(self.anotheruser, PERM_VIEW_ASSET) == True
        assert PERM_VIEW_ASSET in self.asset.get_perms(self.anotheruser)
        assert self.asset.has_perm(self.anotheruser, PERM_CHANGE_ASSET) == True
        assert PERM_CHANGE_ASSET in self.asset.get_perms(self.anotheruser)

        assert (
            self.asset.has_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
            == False
        )
        assert PERM_VIEW_SUBMISSIONS not in self.asset.get_perms(
            self.anotheruser
        )

        self.asset.assign_perm(anonymous_user, PERM_VIEW_SUBMISSIONS)

        assert self.asset.has_perm(self.anotheruser, PERM_VIEW_ASSET) == True
        assert PERM_VIEW_ASSET in self.asset.get_perms(self.anotheruser)

        assert (
            self.asset.has_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS) == True
        )
        assert PERM_VIEW_SUBMISSIONS in self.asset.get_perms(self.anotheruser)

        # resetting permssions of asset
        self.asset.remove_perm(self.anotheruser, PERM_VIEW_ASSET)
        self.asset.remove_perm(self.anotheruser, PERM_CHANGE_ASSET)
        self.asset.remove_perm(anonymous_user, PERM_VIEW_ASSET)
        self.asset.remove_perm(anonymous_user, PERM_VIEW_SUBMISSIONS)

    def test_retrieve_submission_owner(self):
        submission = self.submissions[0]
        url = self.asset.deployment.get_submission_detail_url(submission.get(
            self.asset.deployment.INSTANCE_ID_FIELDNAME))

        response = self.client.get(url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, submission)

    def test_retrieve_submission_not_shared_other(self):
        self._log_in_as_another_user()
        submission = self.submissions[0]
        url = self.asset.deployment.get_submission_detail_url(submission.get(
            self.asset.deployment.INSTANCE_ID_FIELDNAME))
        response = self.client.get(url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_submission_shared_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        submission = self.submissions[0]
        url = self.asset.deployment.get_submission_detail_url(submission.get(
            self.asset.deployment.INSTANCE_ID_FIELDNAME))
        response = self.client.get(url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, submission)

    def test_retrieve_submission_with_partial_permissions(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_VIEW_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }
        self.asset.assign_perm(self.anotheruser, PERM_PARTIAL_SUBMISSIONS,
                               partial_perms=partial_perms)

        # Try first submission submitted by unknown
        submission = self.submissions[0]
        url = self._deployment.get_submission_detail_url(
            submission[self._id_fieldname]
        )
        response = self.client.get(url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Try second submission submitted by someuser
        submission = self.submissions[1]
        url = self._deployment.get_submission_detail_url(
            submission[self._id_fieldname]
        )
        response = self.client.get(url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_submission_owner(self):
        submission = self.submissions[0]
        url = self.asset.deployment.get_submission_detail_url(submission.get(
            self.asset.deployment.INSTANCE_ID_FIELDNAME))

        response = self.client.delete(url,
                                      content_type="application/json",
                                      HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.submission_url, {'format': 'json'})
        # FIXME get submission count for user from Mockbackend
        self.assertEqual(response.data['count'], len(self.submissions) - 1)

    def test_delete_submission_anonymous(self):
        self.client.logout()
        submission = self.submissions[0]
        url = self.asset.deployment.get_submission_detail_url(submission.get(
            self.asset.deployment.INSTANCE_ID_FIELDNAME))

        response = self.client.delete(url,
                                      content_type="application/json",
                                      HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_submission_not_shared_other(self):
        self._log_in_as_another_user()
        submission = self.submissions[0]
        url = self.asset.deployment.get_submission_detail_url(submission.get(
            self.asset.deployment.INSTANCE_ID_FIELDNAME))

        response = self.client.delete(url,
                                      content_type="application/json",
                                      HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_submission_shared_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        submission = self.submissions[0]
        url = self.asset.deployment.get_submission_detail_url(submission.get(
            self.asset.deployment.INSTANCE_ID_FIELDNAME))
        response = self.client.delete(url,
                                      content_type="application/json",
                                      HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # `another_user` should not be able to delete with 'change_submissions'
        # permission.
        self.asset.assign_perm(self.anotheruser, PERM_CHANGE_SUBMISSIONS)
        response = self.client.delete(url,
                                      content_type="application/json",
                                      HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Let's assign them 'delete_submissions'. Everything should be ok then!
        self.asset.assign_perm(self.anotheruser, PERM_DELETE_SUBMISSIONS)
        response = self.client.delete(url,
                                      content_type="application/json",
                                      HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.submission_url, {'format': 'json'})
        # FIXME get submission count for user from Mockbackend
        self.assertEqual(response.data['count'], len(self.submissions) - 1)

    def test_delete_submission_with_partial_perms(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_DELETE_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }

        # Allow anotheruser to delete someuser's data
        self.asset.assign_perm(
            self.anotheruser,
            PERM_PARTIAL_SUBMISSIONS,
            partial_perms=partial_perms,
        )

        # Try first submission submitted by unknown
        submission = self.submissions[0]
        _id = self._id_fieldname
        url = self._deployment.get_submission_detail_url(submission[_id])
        response = self.client.delete(url,
                                      content_type='application/json',
                                      HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try second submission submitted by someuser
        submission = self.submissions[1]
        url = self._deployment.get_submission_detail_url(submission[_id])
        response = self.client.delete(url,
                                      content_type='application/json',
                                      HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.submission_url, {'format': 'json'})
        # FIXME get submission count for user from Mockbackend
        self.assertEqual(response.data['count'], 0)


class SubmissionEditApiTests(BaseSubmissionTestCase):

    def setUp(self):
        super().setUp()
        self.submission = self.submissions[0]
        self.submission_url = reverse(self._get_endpoint('submission-edit'), kwargs={
            'parent_lookup_asset': self.asset.uid,
            'pk': self.submission[self._id_fieldname]
        })

    def test_get_edit_link_submission_owner(self):
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = f'http://server.mock/enketo/{self.submission[self._id_fieldname]}'
        expected_response = {'url': url}
        self.assertEqual(response.data, expected_response)

    def test_get_edit_link_submission_anonymous(self):
        self.client.logout()
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_edit_link_submission_not_shared_other(self):
        self._log_in_as_another_user()
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_edit_link_submission_shared_other_view_only(self):
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_edit_link_submission_shared_other_can_edit(self):
        self.asset.assign_perm(self.anotheruser, PERM_CHANGE_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.get(self.submission_url, {"format": "json"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_edit_link_with_partial_perms(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_CHANGE_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }

        # Allow anotheruser to edit someuser's data
        self.asset.assign_perm(
            self.anotheruser,
            PERM_PARTIAL_SUBMISSIONS,
            partial_perms=partial_perms,
        )

        _id = self._id_fieldname

        # Try first submission submitted by unknown
        submission = self.submissions[0]
        url = reverse(
            self._get_endpoint('submission-edit'),
            kwargs={
                'parent_lookup_asset': self.asset.uid,
                'pk': submission[_id],
            },
        )
        response = self.client.get(url, {'format': 'json'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try second submission submitted by someuser
        submission = self.submissions[1]
        url = reverse(
            self._get_endpoint('submission-edit'),
            kwargs={
                'parent_lookup_asset': self.asset.uid,
                'pk': submission[_id],
            },
        )
        response = self.client.get(url, {'format': 'json'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        url = f'http://server.mock/enketo/{submission[self._id_fieldname]}'
        expected_response = {'url': url}
        self.assertEqual(response.data, expected_response)


class SubmissionDuplicateApiTests(BaseSubmissionTestCase):

    def setUp(self):
        super().setUp()
        v_uid = self.asset.latest_deployed_version.uid
        current_time = datetime.now(tz=pytz.UTC).isoformat('T', 'milliseconds')
        # TODO: also test a submission that's missing `start` or `end`; see
        # #3054. Right now that would be useless, though, because the
        # MockDeploymentBackend doesn't use XML at all and won't fail if an
        # expected field is missing
        for submission in self.submissions:
            submission['start'] = current_time
            submission['end'] = current_time

        self.asset.deployment.mock_submissions(self.submissions)

        self.submission_url = reverse(
            self._get_endpoint('submission-duplicate'),
            kwargs={
                'parent_lookup_asset': self.asset.uid,
                'pk': self.submissions[0].get(
                    self.asset.deployment.INSTANCE_ID_FIELDNAME
                ),
            },
        )

    def _check_duplicate(self, response, submission: dict = None):
        submission = submission if submission else self.submissions[0]
        duplicate_submission = response.data

        expected_next_id = max((sub['_id'] for sub in self.submissions)) + 1
        assert submission['_id'] != duplicate_submission['_id']
        assert duplicate_submission['_id'] == expected_next_id

        assert submission['instanceID'] != duplicate_submission['instanceID']
        assert submission['start'] != duplicate_submission['start']
        assert submission['end'] != duplicate_submission['end']

    def test_duplicate_submission_by_owner_allowed(self):
        response = self.client.post(self.submission_url, {'format': 'json'})
        assert response.status_code == status.HTTP_201_CREATED
        self._check_duplicate(response)

    def test_duplicate_submission_by_anotheruser_not_allowed(self):
        self._log_in_as_another_user()
        response = self.client.post(self.submission_url, {'format': 'json'})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_duplicate_submission_by_anonymous_not_allowed(self):
        self.client.logout()
        response = self.client.post(self.submission_url, {'format': 'json'})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_duplicate_submission_by_anotheruser_shared_view_only_not_allowed(self):
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.post(self.submission_url, {'format': 'json'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_duplicate_submission_by_anotheruser_shared_as_editor_allowed(self):
        self.asset.assign_perm(self.anotheruser, PERM_CHANGE_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.post(self.submission_url, {'format': 'json'})
        assert response.status_code == status.HTTP_201_CREATED
        self._check_duplicate(response)

    def test_duplicate_submission_by_anotheruser_shared_add_not_allowed(self):
        for perm in [PERM_VIEW_SUBMISSIONS, PERM_ADD_SUBMISSIONS]:
            self.asset.assign_perm(self.anotheruser, perm)
        self._log_in_as_another_user()
        response = self.client.post(self.submission_url, {'format': 'json'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_duplicate_submission_with_partial_perms(self):
        self._log_in_as_another_user()

        partial_perms = {
            PERM_CHANGE_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }

        # Allow anotheruser to duplicate someuser's data
        self.asset.assign_perm(
            self.anotheruser,
            PERM_PARTIAL_SUBMISSIONS,
            partial_perms=partial_perms,
        )

        # Try first submission submitted by unknown
        submission = self.submissions[0]
        url = reverse(
            self._get_endpoint('submission-duplicate'),
            kwargs={
                'parent_lookup_asset': self.asset.uid,
                'pk': submission[self._id_fieldname],
            },
        )
        response = self.client.post(url, {'format': 'json'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try second submission submitted by someuser
        submission = self.submissions[1]
        url = reverse(
            self._get_endpoint('submission-duplicate'),
            kwargs={
                'parent_lookup_asset': self.asset.uid,
                'pk': submission[self._id_fieldname],
            },
        )
        response = self.client.post(url, {'format': 'json'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._check_duplicate(response, submission)


class BulkUpdateSubmissionsApiTests(BaseSubmissionTestCase):

    def setUp(self):
        super().setUp()
        self.submission_url = reverse(
            self._get_endpoint('submission-bulk'),
            kwargs={
                'parent_lookup_asset': self.asset.uid,
            },
        )
        self.updated_submission_data = {
            'submission_ids': ['1', '2'],
            'data': {
                'q1': '🕺',
            },
        }

        self.submitted_payload = {
            'payload': self.updated_submission_data
        }

    def _check_bulk_update(self, response):
        submission_ids = self.updated_submission_data['submission_ids']
        # Check that the number of ids given matches the number of successful
        assert len(submission_ids) == response.data['successes']

    def test_bulk_update_submissions_by_owner_allowed(self):
        response = self.client.patch(
            self.submission_url, data=self.submitted_payload, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        self._check_bulk_update(response)

    def test_bulk_update_submissions_by_anotheruser_not_allowed(self):
        self._log_in_as_another_user()
        response = self.client.patch(
            self.submission_url, data=self.submitted_payload, format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_bulk_update_submissions_by_anonymous_not_allowed(self):
        self.client.logout()
        response = self.client.patch(
            self.submission_url, data=self.submitted_payload, format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_bulk_update_submissions_by_anotheruser_shared_view_only_not_allowed(self):
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.patch(
            self.submission_url, data=self.submitted_payload, format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_update_submissions_by_anotheruser_shared_allowed(self):
        self.asset.assign_perm(self.anotheruser, PERM_CHANGE_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.patch(
            self.submission_url, data=self.submitted_payload, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        self._check_bulk_update(response)

    def test_bulk_update_submissions_with_partial_perms(self):
        self._log_in_as_another_user()
        # Allow anotheruser to update someuser's submissions
        partial_perms = {
            PERM_CHANGE_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }

        self.asset.assign_perm(
            self.anotheruser,
            PERM_PARTIAL_SUBMISSIONS,
            partial_perms=partial_perms,
        )
        # Try to update all submissions, but anotheruser is allowed to update
        # someuser's submissions only.
        response = self.client.patch(
            self.submission_url, data=self.submitted_payload, format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Update someuser's submissions
        # TODO retrieve someuser's submission ids dynamically
        self.updated_submission_data['submission_ids'] = [2]
        response = self.client.patch(
            self.submission_url, data=self.submitted_payload, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        self._check_bulk_update(response)


class SubmissionValidationStatusApiTests(BaseSubmissionTestCase):

    def setUp(self):
        super().setUp()
        self.submission = self.submissions[0]
        self.validation_status_url = (
            self._deployment.get_submission_validation_status_url(
                self.submission.get(self._id_fieldname)
            )
        )

    def test_retrieve_submission_validation_status_owner(self):
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.submission.get("_validation_status"))

    def test_retrieve_submission_validation_status_not_shared_other(self):
        self._log_in_as_another_user()
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_submission_validation_status_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VIEW_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.submission.get("_validation_status"))

    def test_retrieve_submission_validation_status_anonymous(self):
        self.client.logout()
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_submission_validation_status_owner(self):
        response = self.client.delete(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Ensure delete worked.
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})

    def test_delete_submission_validation_status_not_shared_other(self):
        self._log_in_as_another_user()
        response = self.client.delete(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_submission_validation_status_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VALIDATE_SUBMISSIONS)
        self._log_in_as_another_user()
        response = self.client.delete(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Ensure delete worked.
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})

    def test_delete_submission_validation_status_anonymous(self):
        self.client.logout()
        response = self.client.delete(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_edit_submission_validation_status_owner(self):
        data = {
            'validation_status.uid': 'validation_status_not_approved'
        }
        response = self.client.patch(self.validation_status_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure update worked.
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['by_whom'], 'someuser')
        self.assertEqual(response.data['uid'], data['validation_status.uid'])

    def test_edit_submission_validation_status_not_shared_other(self):
        self._log_in_as_another_user()
        response = self.client.patch(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_edit_submission_validation_status_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VALIDATE_SUBMISSIONS)
        self._log_in_as_another_user()
        data = {
            'validation_status.uid': 'validation_status_not_approved'
        }
        response = self.client.patch(self.validation_status_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure update worked.
        response = self.client.get(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['by_whom'], 'anotheruser')
        self.assertEqual(response.data['uid'], data['validation_status.uid'])

    def test_edit_submission_validation_status_anonymous(self):
        self.client.logout()
        response = self.client.patch(self.validation_status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_edit_submission_validation_status_with_partial_perms(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_VALIDATE_SUBMISSIONS: [{'_submitted_by': self.someuser.username}]
        }
        # Allow anotheruser to validate someuser's data
        self.asset.assign_perm(self.anotheruser, PERM_PARTIAL_SUBMISSIONS,
                               partial_perms=partial_perms)
        data = {
            'validation_status.uid': 'validation_status_not_approved'
        }

        # Try first submission submitted by unknown
        url = (
            self._deployment.get_submission_validation_status_url(
                self.submissions[0][self._id_fieldname]
            )
        )
        response = self.client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try second submission submitted by someuser
        url = (
            self._deployment.get_submission_validation_status_url(
                self.submissions[1][self._id_fieldname]
            )
        )
        response = self.client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure update worked.
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['by_whom'], 'anotheruser')
        self.assertEqual(response.data['uid'], data['validation_status.uid'])


class SubmissionValidationStatusesApiTests(BaseSubmissionTestCase):

    def setUp(self):
        super().setUp()
        for submission in self.submissions:
            submission['_validation_status']['uid'] = 'validation_status_not_approved'  # noqa
        self.asset.deployment.mock_submissions(self.submissions)
        self.validation_statuses_url = reverse(
            self._get_endpoint('submission-validation-statuses'),
            kwargs={'parent_lookup_asset': self.asset.uid, 'format': 'json'},
        )
        self.submissions_url = reverse(
            self._get_endpoint('submission-list'),
            kwargs={'parent_lookup_asset': self.asset.uid, 'format': 'json'},
        )

    def test_delete_all_submission_validation_statuses_owner(self):
        data = {
            'payload': {
                'validation_status.uid': None,
            }
        }
        response = self.client.delete(self.validation_statuses_url,
                                      data=data,
                                      format='json')
        # `confirm` must me send within payload (when all submissions are
        # modified). Otherwise, a ValidationError is raised
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data['payload']['confirm'] = True
        response = self.client.delete(self.validation_statuses_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = self._deployment.calculated_submission_count(self.someuser.pk)
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Ensure update worked.
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            self.assertEqual(submission['_validation_status'], {})

    def test_delete_some_submission_validation_statuses_owner(self):
        submission_id = 1
        data = {
            'payload': {
                'validation_status.uid': None,
                'submission_ids': [submission_id]
            }
        }
        response = self.client.delete(self.validation_statuses_url,
                                      data=data,
                                      format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = self._deployment.calculated_submission_count(
            self.someuser.pk, instance_ids=[submission_id]
        )
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Ensure update worked.
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            if submission[self._id_fieldname] == submission_id:
                self.assertEqual(submission['_validation_status'], {})
            else:
                self.assertNotEqual(submission['_validation_status'], {})

        # TODO Test with `query` when Mockbackend support Mongo queries

    def test_delete_submission_validation_statuses_not_shared_other(self):
        self._log_in_as_another_user()
        data = {
            'payload': {
                'validation_status.uid': None,
                'confirm': True,
            }
        }
        response = self.client.delete(self.validation_statuses_url,
                                      data=data,
                                      format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_submission_validation_statuses_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VALIDATE_SUBMISSIONS)
        self._log_in_as_another_user()
        data = {
            'payload': {
                'validation_status.uid': None,
                'confirm': True,
            }
        }
        response = self.client.delete(self.validation_statuses_url,
                                      data=data,
                                      format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = self._deployment.calculated_submission_count(self.anotheruser.pk)
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Ensure update worked.
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            self.assertEqual(submission['_validation_status'], {})

    def test_delete_submission_validation_statuses_anonymous(self):
        self.client.logout()
        data = {
            'payload': {
                'validation_status.uid': None,
                'confirm': True,
            }
        }
        response = self.client.delete(self.validation_statuses_url,
                                      data=data,
                                      format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_edit_all_submission_validation_statuses_owner(self):
        data = {
            'payload': {
                'validation_status.uid': 'validation_status_approved',
            }
        }
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        # `confirm` must me send within payload (when all submissions are
        # modified). Otherwise, a ValidationError is raised
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data['payload']['confirm'] = True
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = self._deployment.calculated_submission_count(self.someuser.pk)
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Ensure update worked.
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            validation_status = submission['_validation_status']
            self.assertEqual(validation_status['by_whom'], 'someuser')
            self.assertEqual(
                validation_status['uid'], data['payload']['validation_status.uid']
            )

    def test_edit_some_submission_validation_statuses_owner(self):
        submission_id = 1
        data = {
            'payload': {
                'validation_status.uid': 'validation_status_approved',
                'submission_ids': [submission_id]
            }
        }
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = self._deployment.calculated_submission_count(
            self.someuser.pk, instance_ids=[submission_id]
        )
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Ensure update worked.
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            validation_status = submission['_validation_status']
            if submission[self._id_fieldname] == submission_id:
                self.assertEqual(validation_status['by_whom'], 'someuser')
                self.assertEqual(
                    validation_status['uid'],
                    data['payload']['validation_status.uid']
                )
            else:
                self.assertNotEqual(
                    validation_status['uid'],
                    data['payload']['validation_status.uid']
                )

    def test_edit_submission_validation_statuses_not_shared_other(self):
        self._log_in_as_another_user()
        data = {
            'payload': {
                'validation_status.uid': 'validation_status_approved',
                'confirm': True,
            }
        }
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_edit_submission_validation_statuses_other(self):
        self.asset.assign_perm(self.anotheruser, PERM_VALIDATE_SUBMISSIONS)
        self._log_in_as_another_user()
        data = {
            'payload': {
                'validation_status.uid': 'validation_status_approved',
                'confirm': True,
            }
        }
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = self._deployment.calculated_submission_count(
            self.anotheruser.pk)
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Ensure update worked.
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            validation_status = submission['_validation_status']
            self.assertEqual(validation_status['by_whom'], 'anotheruser')
            self.assertEqual(
                validation_status['uid'],
                data['payload']['validation_status.uid']
            )

    def test_edit_submission_validation_statuses_anonymous(self):
        self.client.logout()
        data = {
            'payload': {
                'validation_status.uid': 'validation_status_approved',
                'confirm': True,
            }
        }
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_edit_all_submission_validation_statuses_with_partial_perms(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_VALIDATE_SUBMISSIONS: [
                {'_submitted_by': self.someuser.username}]
        }
        # Allow anotheruser to validate someuser's data
        self.asset.assign_perm(self.anotheruser, PERM_PARTIAL_SUBMISSIONS,
                               partial_perms=partial_perms)
        data = {
            'payload': {
                'validation_status.uid': 'validation_status_approved',
                'confirm': True,
            }
        }

        # Update all submissions anotheruser is allowed to edit
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        count = self._deployment.calculated_submission_count(
            self.anotheruser.pk)
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Get all submissions and ensure only submissions whose another is only
        # to edit are modified
        self.client.logout()
        self.client.login(username="someuser", password="someuser")
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            validation_status = submission['_validation_status']
            if submission['_submitted_by'] == 'someuser':
                self.assertEqual(validation_status['by_whom'], 'anotheruser')
                self.assertEqual(
                    validation_status['uid'],
                    data['payload']['validation_status.uid']
                )
            else:
                self.assertNotEqual(validation_status['by_whom'], 'anotheruser')
                self.assertNotEqual(
                    validation_status['uid'],
                    data['payload']['validation_status.uid']
                )

    def test_edit_some_submission_validation_statuses_with_partial_perms(self):
        self._log_in_as_another_user()
        partial_perms = {
            PERM_VALIDATE_SUBMISSIONS: [
                {'_submitted_by': self.someuser.username}]
        }
        # Allow anotheruser to validate someuser's data
        self.asset.assign_perm(self.anotheruser, PERM_PARTIAL_SUBMISSIONS,
                               partial_perms=partial_perms)
        data = {
            'payload': {
                'validation_status.uid': 'validation_status_approved',
                'submission_ids': [1]
            }
        }

        # Try first submission submitted by unknown
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try 2nd submission submitted by someuser
        data['payload']['submission_ids'] = [2]
        response = self.client.patch(self.validation_statuses_url,
                                     data=data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        count = self._deployment.calculated_submission_count(
            self.anotheruser.pk, instance_ids=data['payload']['submission_ids'])
        expected_response = {'detail': f'{count} submissions have been updated'}
        self.assertEqual(response.data, expected_response)

        # Get all submissions and ensure only submissions whose another is only
        # to edit are modified
        self.client.logout()
        self.client.login(username="someuser", password="someuser")
        response = self.client.get(self.submissions_url)
        for submission in response.data['results']:
            validation_status = submission['_validation_status']
            if (
                submission[self._id_fieldname]
                in data['payload']['submission_ids']
            ):
                self.assertEqual(validation_status['by_whom'], 'anotheruser')
                self.assertEqual(
                    validation_status['uid'],
                    data['payload']['validation_status.uid']
                )
            else:
                self.assertNotEqual(validation_status['by_whom'], 'anotheruser')
                self.assertNotEqual(
                    validation_status['uid'],
                    data['payload']['validation_status.uid']
                )

        # TODO Test with `query` when Mockbackend support Mongo queries


class SubmissionGeoJsonApiTests(BaseTestCase):

    fixtures = ["test_data"]

    URL_NAMESPACE = ROUTER_URL_NAMESPACE

    def setUp(self):
        self.client.login(username="someuser", password="someuser")
        self.someuser = User.objects.get(username="someuser")
        self.asset = a = Asset()
        a.name = 'Two points and one text'
        a.owner = self.someuser
        a.asset_type = 'survey'
        a.content = {'survey': [
            {'name': 'geo1', 'type': 'geopoint', 'label': 'Where were you?'},
            {'name': 'geo2', 'type': 'geopoint', 'label': 'Where are you?'},
            {'name': 'text', 'type': 'text', 'label': 'How are you?'},
        ]}
        a.save()
        a.deploy(backend='mock', active=True)
        a.save()

        v_uid = a.latest_deployed_version.uid
        self.submissions = [
            {
                '__version__': v_uid,
                'geo1': '10.11 10.12 10.13 10.14',
                'geo2': '10.21 10.22 10.23 10.24',
                'text': 'Tired',
            },
            {
                '__version__': v_uid,
                'geo1': '20.11 20.12 20.13 20.14',
                'geo2': '20.21 20.22 20.23 20.24',
                'text': 'Relieved',
            },
            {
                '__version__': v_uid,
                'geo1': '30.11 30.12 30.13 30.14',
                'geo2': '30.21 30.22 30.23 30.24',
                'text': 'Excited',
            },
        ]
        a.deployment.mock_submissions(self.submissions)
        a.deployment.set_namespace(self.URL_NAMESPACE)
        self.submission_list_url = a.deployment.submission_list_url

    def test_list_submissions_geojson_defaults(self):
        response = self.client.get(
            self.submission_list_url,
            {'format': 'geojson'}
        )
        expected_output = {
            'type': 'FeatureCollection',
            'name': 'Two points and one text',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [10.12, 10.11, 10.13],
                    },
                    'properties': {'text': 'Tired'},
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [20.12, 20.11, 20.13],
                    },
                    'properties': {'text': 'Relieved'},
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [30.12, 30.11, 30.13],
                    },
                    'properties': {'text': 'Excited'},
                },
            ],
        }
        assert expected_output == json.loads(response.content)

    def test_list_submissions_geojson_other_geo_question(self):
        response = self.client.get(
            self.submission_list_url,
            {'format': 'geojson', 'geo_question_name': 'geo2'},
        )
        expected_output = {
            'name': 'Two points and one text',
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'coordinates': [10.22, 10.21, 10.23],
                        'type': 'Point',
                    },
                    'properties': {'text': 'Tired'},
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'coordinates': [20.22, 20.21, 20.23],
                        'type': 'Point',
                    },
                    'properties': {'text': 'Relieved'},
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'coordinates': [30.22, 30.21, 30.23],
                        'type': 'Point',
                    },
                    'properties': {'text': 'Excited'},
                },
            ],
        }
        assert expected_output == json.loads(response.content)
