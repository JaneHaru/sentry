from unittest.mock import Mock, patch

from django.urls import reverse

from sentry.testutils.cases import APITestCase

# TODO: instead of status codes, test the response content and/or template variable passed to iframe.html


class IframeViewTest(APITestCase):
    view_name = "sentry-toolbar-iframe"

    def setUp(self):
        super().setUp()
        self.login_as(user=self.user)
        self.url = reverse(self.view_name, args=(self.organization.slug, self.project.slug))

    def test_missing_project(self):
        url = reverse(self.view_name, args=(self.organization.slug, "abc123xyz"))
        res = self.client.get(url)
        assert res.status_code == 404

    def test_default_no_allowed_origins(self):
        res = self.client.get(self.url, HTTP_REFERER="https://example.com")
        assert res.status_code == 403

    def test_allowed_origins_basic(self):
        self.project.update_option("sentry:toolbar_allowed_origins", ["sentry.io"])
        for referrer in ["https://sentry.io/issues/?a=b/", "https://sentry.io:127/replays/"]:
            res = self.client.get(self.url, HTTP_REFERER=referrer)
            assert res.status_code == 200

    def test_allowed_origins_wildcard_subdomain(self):
        self.project.update_option("sentry:toolbar_allowed_origins", ["*.nugettrends.com"])
        res = self.client.get(self.url, HTTP_REFERER="https://bruno.nugettrends.com")
        assert res.status_code == 200
        res = self.client.get(self.url, HTTP_REFERER="https://andrew.ryan.nugettrends.com")
        assert res.status_code == 403

    def test_no_referrer(self):
        self.project.update_option("sentry:toolbar_allowed_origins", ["sentry.io"])
        res = self.client.get(self.url)
        assert res.status_code == 403

    def test_calls_url_matches(self):
        """
        The `url_matches` helper fx has more in-depth unit test coverage.
        """
        mock_url_matches = Mock(return_value=False)
        allowed_origins = ["sentry.io", "abc.com"]
        referrer = "https://example.com"
        self.project.update_option("sentry:toolbar_allowed_origins", allowed_origins)
        with patch("sentry.toolbar.utils.url.url_matches", mock_url_matches):
            self.client.get(self.url, HTTP_REFERER=referrer)

        assert mock_url_matches.call_count == 2
        for (i, (args, _)) in enumerate(mock_url_matches.call_args_list):
            assert args[0] == referrer
            assert args[1] == allowed_origins[i]

    def test_x_frame_options(self):
        self.project.update_option("sentry:toolbar_allowed_origins", ["https://sentry.io"])
        res = self.client.get(self.url, HTTP_REFERER="https://sentry.io")
        assert res.headers.get("X-Frame-Options") == "ALLOWALL"
