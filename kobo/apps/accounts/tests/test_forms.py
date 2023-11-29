import statistics

from django.urls import reverse
from constance.test import override_config
from django.test import TestCase, override_settings, Client
from django.utils import translation
from hub.models.sitewide_message import SitewideMessage
from model_bakery import baker
from pyquery import PyQuery

from kobo.apps.accounts.forms import SignupForm, SocialSignupForm
from kpi.utils.json import LazyJSONSerializable


class AccountFormsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = baker.make('auth.User')
        cls.sociallogin = baker.make(
            "socialaccount.SocialAccount", user=cls.user
        )

    def setUp(self):
        self.client = Client()
        self.url = reverse('account_signup')

    @override_settings(UNSAFE_SSO_REGISTRATION_EMAIL_DISABLE=True)
    def test_social_signup_form_not_email_disabled(self):
        form = SocialSignupForm(sociallogin=self.sociallogin)
        pq = PyQuery(str(form))
        assert (email_input := pq("[name=email]"))
        assert "readonly" in email_input[0].attrib

    @override_settings(UNSAFE_SSO_REGISTRATION_EMAIL_DISABLE=False)
    def test_social_signup_form_not_email_not_disabled(self):
        form = SocialSignupForm(sociallogin=self.sociallogin)
        pq = PyQuery(str(form))
        assert (email_input := pq("[name=email]"))
        assert "readonly" not in email_input[0].attrib

    def test_only_configurable_fields_can_be_removed(self):
        with override_config(USER_METADATA_FIELDS='{}'):
            form = SocialSignupForm(sociallogin=self.sociallogin)
            assert 'username' in form.fields
            assert 'email' in form.fields

    def test_field_without_custom_label_can_be_required(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [{'name': 'name', 'required': True}]
            )
        ):
            form = SocialSignupForm(sociallogin=self.sociallogin)
            assert form.fields['name'].required
            assert form.fields['name'].label == 'Full name'

    def test_field_with_only_default_custom_label(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'name',
                        'required': True,
                        'label': {'default': 'Secret Agent ID'},
                    }
                ]
            )
        ):
            form = SocialSignupForm(sociallogin=self.sociallogin)
            assert form.fields['name'].required
            assert form.fields['name'].label == 'Secret Agent ID'

    def test_field_with_specific_and_default_custom_labels(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'name',
                        'required': True,
                        'label': {
                            'default': 'Secret Agent ID',
                            'es': 'ID de agente secreto',
                        },
                    }
                ]
            )
        ):
            with translation.override('es'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['name'].required
                assert form.fields['name'].label == 'ID de agente secreto'
            with translation.override('en'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['name'].required
                assert form.fields['name'].label == 'Secret Agent ID'
            with translation.override('fr'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['name'].required
                assert form.fields['name'].label == 'Secret Agent ID'

    def test_field_with_custom_label_without_default(self):
        """
        The JSON schema should always require a default label, but the form
        should render labels properly even if the default is missing
        """
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'organization',
                        'required': True,
                        'label': {
                            'fr': 'Organisation secrète',
                        },
                    },
                ]
            )
        ):
            with translation.override('fr'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['organization'].required
                assert (
                    form.fields['organization'].label == 'Organisation secrète'
                )

    def test_field_without_custom_label_can_be_optional(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'organization',
                        'required': False,
                    },
                ]
            )
        ):
            form = SocialSignupForm(sociallogin=self.sociallogin)
            assert not form.fields['organization'].required

    def test_field_with_custom_label_can_be_optional(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'organization',
                        'required': False,
                        'label': {
                            'default': 'Organization',
                            'fr': 'Organisation',
                            'es': 'Organización',
                        },
                    },
                ]
            )
        ):
            form = SocialSignupForm(sociallogin=self.sociallogin)
            assert not form.fields['organization'].required
            assert form.fields['organization'].label == 'Organization'
            with translation.override('fr'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['organization'].required is False
                assert form.fields['organization'].label == 'Organisation'
            with translation.override('es'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['organization'].required is False
                assert form.fields['organization'].label == 'Organización'

    def test_not_supported_translation(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'organization',
                        'required': False,
                        'label': {
                            'default': 'Organization',
                            'fr': 'Organisation',
                        },
                    },
                ]
            )
        ):
            with translation.override('es'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['organization'].required is False
                assert form.fields['organization'].label == 'Organization'
            with translation.override('ar'):
                form = SocialSignupForm(sociallogin=self.sociallogin)
                assert form.fields['organization'].required is False
                assert form.fields['organization'].label == 'Organization'

    def test_organization_field_skip_logic(self):
        basic_data = {
            'username': 'foo',
            'email': 'double@foo.bar',
            'password1': 'tooxox',
            'password2': 'tooxox',
        }

        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {'name': 'organization_type', 'required': False},
                    {'name': 'organization', 'required': False},
                    {'name': 'organization_website', 'required': False},
                ]
            )
        ):
            form = SignupForm(basic_data)
            assert form.is_valid()

            data = basic_data.copy()
            data['organization_type'] = 'government'
            form = SignupForm(data)
            # No other organization fields should be required
            assert form.is_valid()

        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {'name': 'organization_type', 'required': True},
                    {'name': 'organization', 'required': False},
                    {'name': 'organization_website', 'required': False},
                ]
            )
        ):
            form = SignupForm(basic_data)
            # Should fail now that `organization_type` is required
            assert not form.is_valid()

            data = basic_data.copy()
            data['organization_type'] = 'government'
            form = SignupForm(data)
            # No other organization fields should be required
            assert form.is_valid()

        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {'name': 'organization_type', 'required': True},
                    {'name': 'organization', 'required': True},
                    {'name': 'organization_website', 'required': True},
                ]
            )
        ):
            form = SignupForm(basic_data)
            assert not form.is_valid()

            data = basic_data.copy()
            data['organization_type'] = 'government'
            data['organization'] = 'ministry of love'
            data['organization_website'] = 'https://minilove.test'
            form = SignupForm(data)
            assert form.is_valid()

            data = basic_data.copy()
            data['organization_type'] = 'none'
            # The special string 'none' should cause the required-ness of other
            # organization fields to be ignored
            form = SignupForm(data)
            assert form.is_valid()

    def test_organization_type_valid_field(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'organization_type',
                        'required': False,
                    },
                ]
            )
        ):
            form = SocialSignupForm(sociallogin=self.sociallogin)
            assert 'organization_type' in form.fields

    def test_newsletter_subscription_valid_field(self):
        with override_config(
            USER_METADATA_FIELDS=LazyJSONSerializable(
                [
                    {
                        'name': 'newsletter_subscription',
                        'required': False,
                    },
                ]
            )
        ):
            form = SocialSignupForm(sociallogin=self.sociallogin)
            assert 'newsletter_subscription' in form.fields

    def test_tos_checkbox(self):
        # WIP
        SitewideMessage.objects.create(
            slug='terms_of_service',
            body='tos agreement',
        )

        form = SocialSignupForm(sociallogin=self.sociallogin)
        assert 'terms_of_service' in form.fields

        response = self.client.post(self.url)
        breakpoint()
        assert response.status_code == 200
