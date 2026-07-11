from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from organizations.models import Organization, OrganizationMember
from rest_framework.test import APITestCase
from users.models import User


def create_user(email, organization=None):
    user = User.objects.create(email=email, username=email.split('@')[0])
    if organization is not None:
        organization.add_user(user)
        user.active_organization = organization
        user.save(update_fields=['active_organization'])
    return user


class TestOrganizationMemberResetPasswordAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('owner@example.com')
        cls.organization = Organization.create_organization(created_by=cls.owner, title='Label Studio')
        cls.owner.active_organization = cls.organization
        cls.owner.save(update_fields=['active_organization'])

        cls.admin = create_user('admin@example.com', cls.organization)
        cls.annotator = create_user('annotator@example.com', cls.organization)
        OrganizationMember.objects.filter(user=cls.admin, organization=cls.organization).update(
            role=OrganizationMember.Role.ADMIN
        )

    def get_url(self, user):
        return f'/api/organizations/{self.organization.id}/memberships/{user.id}/reset-password'

    def test_non_admin_cannot_reset_password(self):
        self.client.force_authenticate(user=self.annotator)

        response = self.client.post(self.get_url(self.admin), format='json')

        assert response.status_code == 403

    def test_admin_cannot_reset_own_password(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.get_url(self.admin), format='json')

        assert response.status_code == 403

    def test_admin_cannot_reset_owner_password(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.get_url(self.owner), format='json')

        assert response.status_code == 403

    def test_admin_can_reset_member_password(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.get_url(self.annotator), format='json')

        assert response.status_code == 200
        reset_url = response.json()['reset_url']
        assert reset_url

        uidb64, token = reset_url.rstrip('/').split('/')[-2:]
        uid = force_str(urlsafe_base64_decode(uidb64))
        assert int(uid) == self.annotator.id
        assert default_token_generator.check_token(self.annotator, token)

    def test_reset_password_view_changes_password_and_invalidates_token(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.get_url(self.annotator), format='json')
        reset_url = response.json()['reset_url']

        new_password = 'a-brand-new-password-1'
        set_password_response = self.client.post(
            reset_url, {'password': new_password, 'password_confirm': new_password}
        )

        assert set_password_response.status_code == 302
        self.annotator.refresh_from_db()
        assert self.annotator.check_password(new_password)

        uidb64, token = reset_url.rstrip('/').split('/')[-2:]
        assert not default_token_generator.check_token(self.annotator, token)
