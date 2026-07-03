from organizations.models import Organization, OrganizationMember
from projects.models import Project, ProjectMember
from rest_framework.test import APITestCase
from users.models import User


def create_user(email, organization=None):
    user = User.objects.create(email=email, username=email.split('@')[0])
    if organization is not None:
        organization.add_user(user)
        user.active_organization = organization
        user.save(update_fields=['active_organization'])
    return user


class TestOrganizationRBAC(APITestCase):
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

    def test_owner_can_update_member_role(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f'/api/organizations/{self.organization.id}/memberships/{self.annotator.id}/',
            {'role': OrganizationMember.Role.MANAGER},
            format='json',
        )

        assert response.status_code == 200
        assert response.json()['role'] == OrganizationMember.Role.MANAGER
        assert OrganizationMember.objects.get(user=self.annotator, organization=self.organization).role == 'manager'

    def test_annotator_cannot_create_project(self):
        self.client.force_authenticate(user=self.annotator)

        response = self.client.post('/api/projects', {'title': 'Blocked project'}, format='json')

        assert response.status_code == 403

    def test_annotator_only_sees_assigned_projects(self):
        assigned = Project.objects.create(title='assigned', organization=self.organization, created_by=self.owner)
        unassigned = Project.objects.create(title='unassigned', organization=self.organization, created_by=self.owner)
        ProjectMember.objects.create(user=self.annotator, project=assigned)

        titles = set(Project.objects.for_user(self.annotator).values_list('title', flat=True))

        assert assigned.title in titles
        assert unassigned.title not in titles

    def test_patch_cannot_reassign_member_user_or_organization(self):
        self.client.force_authenticate(user=self.owner)
        other_org = Organization.create_organization(created_by=create_user('other-owner@example.com'), title='Other')

        response = self.client.patch(
            f'/api/organizations/{self.organization.id}/memberships/{self.annotator.id}/',
            {'role': OrganizationMember.Role.MANAGER, 'user': self.admin.id, 'organization': other_org.id},
            format='json',
        )

        assert response.status_code == 200
        member = OrganizationMember.objects.get(user=self.annotator, organization=self.organization)
        assert member.role == 'manager'
        assert member.user_id == self.annotator.id
        assert member.organization_id == self.organization.id

    def test_owner_cannot_be_soft_deleted(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(f'/api/organizations/{self.organization.id}/memberships/{self.owner.id}/')

        assert response.status_code == 403
        assert OrganizationMember.objects.get(user=self.owner, organization=self.organization).deleted_at is None


class TestOrganizationCreatePermission(APITestCase):
    def test_orgless_user_can_create_organization(self):
        user = create_user('fresh@example.com')
        self.client.force_authenticate(user=user)

        response = self.client.post('/api/organizations', {'title': 'Fresh Org'}, format='json')

        assert response.status_code == 201
