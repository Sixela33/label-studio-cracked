import { useCallback, useEffect, useState } from "react";
import { Button, Typography } from "@humansignal/ui";
import { ABILITY, useAuth } from "@humansignal/core/providers/AuthProvider";
import { createTitleFromSegments, useUpdatePageTitle } from "@humansignal/core";
import { Spinner } from "../../components/Spinner/Spinner";
import { useAPI } from "../../providers/ApiProvider";
import { useProject } from "../../providers/ProjectProvider";
import { cn } from "../../utils/bem";

export const ProjectMembersSettings = () => {
  const api = useAPI();
  const { project } = useProject();
  const { permissions } = useAuth();
  const canManageMembers = permissions.can(ABILITY.can_change_projects);
  const [members, setMembers] = useState(null);
  const [processingUser, setProcessingUser] = useState(null);
  const [error, setError] = useState(null);

  useUpdatePageTitle(createTitleFromSegments([project?.title, "Members"]));

  const fetchMembers = useCallback(async () => {
    if (!project?.id || !canManageMembers) return;

    setError(null);
    const response = await api.callApi("projectMembers", {
      params: { pk: project.id },
      errorFilter: () => true,
    });

    if (response?.$meta?.ok === false) {
      setError("Could not load project members.");
      return;
    }

    setMembers(response);
  }, [api, project?.id, canManageMembers]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  const updateMember = useCallback(
    async (member, enabled) => {
      setProcessingUser(member.user.id);
      setError(null);

      const response = enabled
        ? await api.callApi("addProjectMember", {
            params: { pk: project.id },
            body: { user_id: member.user.id },
            errorFilter: () => true,
          })
        : await api.callApi("removeProjectMember", {
            params: { pk: project.id, userPk: member.user.id },
            errorFilter: () => true,
          });

      setProcessingUser(null);

      if (response?.$meta?.ok === false) {
        setError("Could not update project member access.");
        return;
      }

      await fetchMembers();
    },
    [api, project?.id, fetchMembers],
  );

  return (
    <div className={cn("simple-settings").toClassName()}>
      <h1>Members</h1>
      <p className={cn("settings-description").toClassName()}>
        Control which organization members can access this project.
      </p>

      <div className={cn("settings-wrapper").toClassName()}>
        {!canManageMembers ? (
          <Typography size="small" className="text-neutral-content-subtler">
            Contact an administrator to manage project members.
          </Typography>
        ) : members === null ? (
          <div className="flex justify-center items-center h-32">
            <Spinner />
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {error && (
              <Typography size="small" className="text-negative-content">
                {error}
              </Typography>
            )}
            {members.map((member) => {
              const name = [member.user.first_name, member.user.last_name].filter(Boolean).join(" ");
              const displayName = name || member.user.email || member.user.username;
              const isProcessing = processingUser === member.user.id;
              const hasRoleAccess = member.inherited_access;

              return (
                <div
                  key={member.user.id}
                  className="flex justify-between items-center border border-neutral-border rounded-lg p-3"
                >
                  <div>
                    <Typography variant="body" size="medium">
                      {displayName}
                    </Typography>
                    <Typography size="small" className="text-neutral-content-subtler">
                      {member.user.email} · {member.effective_role}
                      {hasRoleAccess ? " · Access from role" : ""}
                    </Typography>
                  </div>
                  <Button
                    look={member.enabled ? "outlined" : "filled"}
                    disabled={isProcessing || hasRoleAccess}
                    onClick={() => updateMember(member, !member.enabled)}
                  >
                    {hasRoleAccess ? "Included" : member.enabled ? "Remove" : "Add"}
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

ProjectMembersSettings.menuItem = "Members";
ProjectMembersSettings.path = "/members";
ProjectMembersSettings.exact = true;
