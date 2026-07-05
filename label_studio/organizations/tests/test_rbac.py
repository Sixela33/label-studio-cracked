from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from organizations.models import Organization, OrganizationMember
from projects.models import Project, ProjectMember
from rest_framework.test import APITestCase
from users.functions.common import save_user
from users.models import PlatformOwner, User


def create_user(email, organization=None):
    user = User.objects.create(email=email, username=email.split('@')[0])
    if organization is not None:
        organization.add_user(user)
        user.active_organization = organization
        user.save(update_fields=['active_organization'])
    return user


class _FakeUserForm:
    def __init__(self, user):
        self._user = user
        self.cleaned_data = {}

    def save(self):
        return self._user


def run_save_user(user):
    request = RequestFactory().post('/user/signup/')
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    save_user(request, None, _FakeUserForm(user))


class TestOrganizationRBAC(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user('owner@example.com')
        cls.organization = Organization.create_organization(created_by=cls.owner, title='Label Studio')
        cls.owner.active_organization = cls.organization
        cls.owner.save(update_fields=['active_organization'])

        cls.admin = create_user('admin@example.com', cls.organization)
        cls.manager = create_user('manager@example.com', cls.organization)
        cls.annotator = create_user('annotator@example.com', cls.organization)
        OrganizationMember.objects.filter(user=cls.admin, organization=cls.organization).update(
            role=OrganizationMember.Role.ADMIN
        )
        OrganizationMember.objects.filter(user=cls.manager, organization=cls.organization).update(
            role=OrganizationMember.Role.MANAGER
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

    def test_manager_cannot_create_project_by_default(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post('/api/projects', {'title': 'Blocked project'}, format='json')

        assert response.status_code == 403

    def test_admin_can_create_project(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post('/api/projects', {'title': 'Admin project'}, format='json')

        assert response.status_code == 201

    def test_platform_owner_can_create_project_without_org_owner_role(self):
        PlatformOwner.objects.create(user=self.manager)
        self.client.force_authenticate(user=self.manager)

        response = self.client.post('/api/projects', {'title': 'Platform owner project'}, format='json')

        assert response.status_code == 201

    def test_annotator_only_sees_assigned_projects(self):
        assigned = Project.objects.create(title='assigned', organization=self.organization, created_by=self.owner)
        unassigned = Project.objects.create(title='unassigned', organization=self.organization, created_by=self.owner)
        ProjectMember.objects.create(user=self.annotator, project=assigned)

        titles = set(Project.objects.for_user(self.annotator).values_list('title', flat=True))

        assert assigned.title in titles
        assert unassigned.title not in titles

    def test_admin_can_manage_project_members(self):
        project = Project.objects.create(title='managed', organization=self.organization, created_by=self.owner)
        self.client.force_authenticate(user=self.admin)

        add_response = self.client.post(
            f'/api/projects/{project.id}/members/',
            {'user_id': self.annotator.id},
            format='json',
        )
        list_response = self.client.get(f'/api/projects/{project.id}/members/')

        assert add_response.status_code == 204
        assert ProjectMember.objects.filter(project=project, user=self.annotator, enabled=True).exists()
        assert list_response.status_code == 200
        assert any(
            member['user']['id'] == self.annotator.id and member['enabled'] for member in list_response.json()
        )

    def test_admin_can_remove_project_member(self):
        project = Project.objects.create(title='managed', organization=self.organization, created_by=self.owner)
        ProjectMember.objects.create(user=self.annotator, project=project)
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(f'/api/projects/{project.id}/members/{self.annotator.id}/')

        assert response.status_code == 204
        assert ProjectMember.objects.get(project=project, user=self.annotator).enabled is False

    def test_annotator_cannot_manage_project_members(self):
        project = Project.objects.create(title='managed', organization=self.organization, created_by=self.owner)
        ProjectMember.objects.create(user=self.annotator, project=project)
        self.client.force_authenticate(user=self.annotator)

        response = self.client.get(f'/api/projects/{project.id}/members/')

        assert response.status_code == 403

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

    def test_annotator_can_list_users_of_assigned_project(self):
        from tasks.models import Annotation, Task

        project = Project.objects.create(title='scoped', organization=self.organization, created_by=self.owner)
        ProjectMember.objects.create(user=self.annotator, project=project)
        # A contributor who annotated the project but is NOT a project member.
        contributor = create_user('contributor@example.com', self.organization)
        task = Task.objects.create(project=project, data={})
        Annotation.objects.create(task=task, project=project, completed_by=contributor)
        self.client.force_authenticate(user=self.annotator)

        response = self.client.get(f'/api/users/?project={project.id}')

        assert response.status_code == 200
        returned_ids = {user['id'] for user in response.json()}
        assert self.annotator.id in returned_ids  # assigned member
        assert contributor.id in returned_ids  # annotation author
        assert self.admin.id not in returned_ids  # non-participant excluded

    def test_annotator_cannot_list_users_of_unassigned_project(self):
        project = Project.objects.create(title='other', organization=self.organization, created_by=self.owner)
        self.client.force_authenticate(user=self.annotator)

        response = self.client.get(f'/api/users/?project={project.id}')

        assert response.status_code == 403

    def test_annotator_cannot_list_users_without_project_scope(self):
        self.client.force_authenticate(user=self.annotator)

        response = self.client.get('/api/users/')

        assert response.status_code == 403

    def test_admin_can_list_users_of_project(self):
        project = Project.objects.create(title='admin-scoped', organization=self.organization, created_by=self.owner)
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(f'/api/users/?project={project.id}')

        assert response.status_code == 200

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


class TestPlatformOwnerAssignment(APITestCase):
    def test_signup_creates_platform_owner_for_first_user(self):
        user = User.objects.create(email='first-owner@example.com', username='first-owner')

        run_save_user(user)

        assert PlatformOwner.objects.filter(user=user).exists()

    def test_signup_keeps_existing_first_user_as_platform_owner(self):
        first = User.objects.create(email='first@example.com', username='first')
        second = User.objects.create(email='second@example.com', username='second')

        run_save_user(second)

        assert PlatformOwner.objects.filter(user=first).exists()
        assert not PlatformOwner.objects.filter(user=second).exists()
