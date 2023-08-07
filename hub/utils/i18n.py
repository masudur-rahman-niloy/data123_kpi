# coding: utf-8
import json
import logging

import constance
from django.db.models import Q
from django.db.models.functions import Length
from django.utils.translation import get_language, gettext as t

from kpi.utils.log import logging
from ..models import SitewideMessage


class I18nUtils:

    @staticmethod
    def get_sitewide_message(slug="welcome_message", lang=None):
        """
        Returns a sitewide message based on its slug and the specified language.
        If the language is not specified, it will use the current language.
        If there are no results found, it falls back on the global version.
        It doesn't exist at all, it returns None.
        :param slug: str
        :param lang: str|None
        :return: MarkupField|None
        """

        # Get default value if lang is not specified
        language = lang if lang else get_language()

        # Let's retrieve messages where slug is either:
        #   - "<slug>_<locale>"
        #   - "<slug>"
        # We order the results by the length of the slug to be sure
        # localized version comes first.
        sitewide_message = SitewideMessage.objects\
            .filter(
                Q(slug="{}_{}".format(slug, language)) |
                Q(slug="{}".format(slug)))\
            .order_by(Length("slug").desc())\
            .first()

        if sitewide_message is not None:
            return sitewide_message.body

        return None

    @staticmethod
    def get_mfa_help_text(lang=None):
        """
        Returns a localized version of the text for MFA guidance
        """

        # Get default value if lang is not specified
        language = lang if lang else get_language()

        try:
            messages_dict = json.loads(constance.config.MFA_LOCALIZED_HELP_TEXT)
        except json.JSONDecodeError:
            logging.error(
                'Configuration value for MFA_LOCALIZED_HELP_TEXT has invalid '
                'JSON'
            )
            # Given the validation done in the django admin interface, this
            # is an acceptable, low-likelihood evil
            return ''
        try:
            message = messages_dict[language]
        except KeyError:
            # Fall back to a default, which could be either:
            #   * A static string from `CONSTANCE_CONFIG`, which itself is
            #     translated, or,
            #   * The superuser's customized default.
            # If it's the former, calling `t()` will return a translated string
            # (if available) from the Django gettext machinery. If it's the
            # latter, then `t()` won't do anything useful, but it won't hurt
            # either
            message = t(messages_dict['default'])

        message = message.replace(
            '##support email##',
            constance.config.SUPPORT_EMAIL,
        )
        return message
