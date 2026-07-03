import { format } from "date-fns";
import { NavLink } from "react-router-dom";
import { IconCross } from "@humansignal/icons";
import { Userpic, Button } from "@humansignal/ui";
import { useState } from "react";
import { cn } from "../../../utils/bem";
import "./SelectedUser.prefix.css";

const UserProjectsLinks = ({ projects }) => {
  return (
    <div className={cn("user-info").elem("links-list").toClassName()}>
      {projects.map((project) => (
        <NavLink
          className={cn("user-info").elem("project-link").toClassName()}
          key={`project-${project.id}`}
          to={`/projects/${project.id}`}
          data-external
        >
          {project.title}
        </NavLink>
      ))}
    </div>
  );
};

export const SelectedUser = ({ user, canManageRoles, onRoleChange, onClose }) => {
  const fullName = [user.first_name, user.last_name]
    .filter((n) => !!n)
    .join(" ")
    .trim();

  const [savingRole, setSavingRole] = useState(false);
  const effectiveRole = user.effective_role || user.role;
  const canEditRole = canManageRoles && effectiveRole !== "owner";

  const changeRole = async (event) => {
    const role = event.target.value;

    setSavingRole(true);
    try {
      await onRoleChange?.(user, role);
    } finally {
      setSavingRole(false);
    }
  };

  return (
    <div className={cn("user-info").toClassName()}>
      <Button
        look="string"
        onClick={onClose}
        className="absolute top-[20px] right-[24px]"
        aria-label="Close user details"
      >
        <IconCross />
      </Button>

      <div className={cn("user-info").elem("header").toClassName()}>
        <Userpic user={user} style={{ width: 64, height: 64, fontSize: 28 }} />
        <div className={cn("user-info").elem("info-wrapper").toClassName()}>
          {fullName && <div className={cn("user-info").elem("full-name").toClassName()}>{fullName}</div>}
          <p className={cn("user-info").elem("email").toClassName()}>{user.email}</p>
        </div>
      </div>

      {user.phone && (
        <div className={cn("user-info").elem("section").toClassName()}>
          <a href={`tel:${user.phone}`}>{user.phone}</a>
        </div>
      )}

      <div className={cn("user-info").elem("section").toClassName()}>
        <div className={cn("user-info").elem("section-title").toClassName()}>Role</div>
        {canEditRole ? (
          <select value={user.role} disabled={savingRole} onChange={changeRole} aria-label="Member role">
            <option value="admin">Admin</option>
            <option value="manager">Manager</option>
            <option value="annotator">Annotator</option>
          </select>
        ) : (
          <span className={cn("user-info").elem("role").toClassName()}>{effectiveRole}</span>
        )}
      </div>

      {!!user.created_projects.length && (
        <div className={cn("user-info").elem("section").toClassName()}>
          <div className={cn("user-info").elem("section-title").toClassName()}>Created Projects</div>

          <UserProjectsLinks projects={user.created_projects} />
        </div>
      )}

      {!!user.contributed_to_projects.length && (
        <div className={cn("user-info").elem("section").toClassName()}>
          <div className={cn("user-info").elem("section-title").toClassName()}>Contributed to</div>

          <UserProjectsLinks projects={user.contributed_to_projects} />
        </div>
      )}

      <p className={cn("user-info").elem("last-active").toClassName()}>
        Last activity on: {format(new Date(user.last_activity), "dd MMM yyyy, KK:mm a")}
      </p>
    </div>
  );
};
